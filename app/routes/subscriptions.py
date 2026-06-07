import json
import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, Header, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from math import ceil
from datetime import datetime, timedelta, timezone

from app.auth import get_current_user, get_tenant_id_from_header, CurrentUser
from app.config import get_settings
from app.database import get_db
from app.models.subscription import SubscriptionRead, SubscriptionWithPlan, PaymentProvider
from app.models.plan import (
    PlanRead, PlanWithLimits, PlanLimitRead,
    PlanAddonRead, CustomPlanRequest, CustomPlanCalculation,
    CustomPlanRead, AddonLineItem,
)
from app.services.membership_service import require_owner
from app.services.permission_service import require_permission
from app.services.audit_service import log_audit
from app.services.paypal_service import get_paypal_service

CUSTOM_PLAN_MIN_PRICE = 150.00  # الحد الأدنى للباقة المخصصة (ريال/شهر)
YEARLY_DISCOUNT_MONTHS = 10     # السنوي = شهري × 10 (خصم شهرين)

settings = get_settings()
stripe.api_key = settings.stripe_secret_key
paypal_service = get_paypal_service()

router = APIRouter(tags=["Subscriptions & Plans"])


def _resolve_app_url(request: Request) -> str:
    origin = request.headers.get("origin")
    if origin:
        return origin.rstrip("/")

    referer = request.headers.get("referer")
    if referer:
        parts = referer.split("/", 3)
        if len(parts) >= 3:
            return f"{parts[0]}//{parts[2]}".rstrip("/")

    return settings.app_url.rstrip("/")


def _resolve_paypal_currency(plan_currency: str | None) -> str:
    if settings.paypal_currency:
        return settings.paypal_currency.upper()
    if settings.paypal_mode.lower() == "sandbox":
        return "USD"
    return (plan_currency or "USD").upper()


# ══════════════════════════════════════════════
# PLANS (public)
# ══════════════════════════════════════════════

@router.get("/plans", response_model=list[PlanWithLimits])
async def list_plans(db: AsyncSession = Depends(get_db)):
    """List all active plans with their limits."""
    try:
        plans_result = await db.execute(
            text("""
                SELECT id, code, name, description, subtitle,
                       price_monthly, price_yearly, :display_currency AS currency, is_active, sort_order,
                       badge_color, is_popular, is_customizable, features
                FROM plans
                WHERE is_active = true
                ORDER BY sort_order
            """)
            ,
            {"display_currency": _resolve_paypal_currency(None)},
        )
        plans = plans_result.mappings().all()

        result = []
        for plan in plans:
            limits_result = await db.execute(
                text("SELECT id, plan_id, key, value, period FROM plan_limits WHERE plan_id = :pid"),
                {"pid": str(plan["id"])},
            )
            limits = [PlanLimitRead(**dict(l)) for l in limits_result.mappings().all()]
            plan_dict = dict(plan)
            # features is stored as JSONB — ensure it's a list
            features_raw = plan_dict.get("features")
            if features_raw is None:
                plan_dict["features"] = []
            elif isinstance(features_raw, str):
                import json
                plan_dict["features"] = json.loads(features_raw)
            result.append(PlanWithLimits(**plan_dict, limits=limits))
        return result
    except SQLAlchemyError:
        await db.rollback()

    # Local lightweight schema fallback: plans.slug exists, plan_limits may not.
    plans_result = await db.execute(
        text("""
            SELECT
                id,
                slug AS code,
                name,
                price_monthly,
                price_yearly,
                :display_currency AS currency,
                true AS is_active,
                row_number() OVER (ORDER BY price_monthly, name)::int AS sort_order
            FROM plans
            ORDER BY price_monthly, name
        """),
        {"display_currency": _resolve_paypal_currency(None)},
    )
    return [PlanWithLimits(**dict(plan), limits=[]) for plan in plans_result.mappings().all()]


# ══════════════════════════════════════════════
# SUBSCRIPTIONS
# ══════════════════════════════════════════════

@router.get("/subscriptions/current", response_model=SubscriptionWithPlan)
async def get_current_subscription(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the active subscription for the current tenant."""
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "settings.view")

    result = await db.execute(
        text("""
            SELECT
                s.*,
                p.code AS plan_code,
                p.name AS plan_name,
                p.price_monthly,
                p.price_yearly,
                :display_currency AS currency
            FROM subscriptions s
            JOIN plans p ON p.id = s.plan_id
            WHERE s.tenant_id = :tid AND s.status IN ('active', 'trialing')
            ORDER BY s.created_at DESC
            LIMIT 1
        """),
        {"tid": str(tenant_id), "display_currency": _resolve_paypal_currency(None)},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="No active subscription")
    return SubscriptionWithPlan(**dict(row))


# ── Create PayPal Checkout Session ──
@router.post("/subscriptions/checkout")
async def create_checkout_session(
    plan_code: str,
    request: Request,
    payment_provider: str = "paypal",
    billing_period: str = "monthly",
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a PayPal Checkout session for upgrading/changing plan."""
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "settings.manage")

    billing_period = billing_period.lower()
    if billing_period not in {"monthly", "yearly"}:
        raise HTTPException(status_code=400, detail="Unsupported billing period")

    if payment_provider.lower() != "paypal":
        raise HTTPException(status_code=400, detail="Unsupported payment provider")

    # Get plan
    plan_result = await db.execute(
        text("SELECT id, code, name, currency, price_monthly, price_yearly FROM plans WHERE code = :code AND is_active = true"),
        {"code": plan_code},
    )
    plan = plan_result.mappings().first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    # Check if PayPal is configured
    if not paypal_service.is_configured():
        raise HTTPException(status_code=503, detail="PayPal is not configured on the server yet")

    amount = float(plan["price_yearly"] if billing_period == "yearly" else plan["price_monthly"])
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Selected plan cannot be purchased through checkout")

    app_url = _resolve_app_url(request)

    # Create PayPal billing plan
    paypal_plan = paypal_service.create_billing_plan(
        plan_code=plan_code,
        plan_name=plan["name"],
        description=f"Subscription to {plan['name']}",
        amount=amount,
        currency=_resolve_paypal_currency(plan["currency"]),
        billing_period=billing_period,
        app_url=app_url,
    )

    if not paypal_plan:
        raise HTTPException(status_code=500, detail="Failed to create PayPal billing plan")

    # Create PayPal subscription agreement
    subscription = paypal_service.create_subscription(
        plan_id=paypal_plan["id"],
        payer_email=user.email,
        metadata={
            "tenant_id": str(tenant_id),
            "plan_code": plan_code,
            "billing_period": billing_period,
        },
    )

    if not subscription:
        raise HTTPException(status_code=500, detail="Failed to create PayPal subscription")

    await db.execute(
        text("""
            INSERT INTO pending_subscriptions (tenant_id, plan_id, provider, provider_agreement_id, payer_email, metadata)
            VALUES (:tid, (SELECT id FROM plans WHERE code = :plan_code), 'paypal', :agreement_id, :email, CAST(:metadata AS jsonb))
        """),
        {
            "tid": str(tenant_id),
            "plan_code": plan_code,
            "agreement_id": subscription["id"],
            "email": user.email,
            "metadata": json.dumps({
                "tenant_id": str(tenant_id),
                "plan_code": plan_code,
                "plan_name": plan["name"],
                "billing_period": billing_period,
                "paypal_token": subscription.get("token"),
                "app_url": app_url,
            })
        }
    )
    await db.commit()

    return {
        "checkout_url": subscription["approval_url"],
        "session_id": subscription["id"],
        "token": subscription["token"]
    }


@router.post("/subscriptions/change-plan")
async def change_plan_without_checkout(
    plan_code: str,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change to a non-paid plan without external checkout."""
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "settings.manage")

    plan_result = await db.execute(
        text("SELECT id, code, name, price_monthly, price_yearly FROM plans WHERE code = :code AND is_active = true"),
        {"code": plan_code},
    )
    plan = plan_result.mappings().first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    if float(plan["price_monthly"] or 0) > 0 or float(plan["price_yearly"] or 0) > 0:
        raise HTTPException(status_code=400, detail="Paid plans require checkout")

    await db.execute(
        text("UPDATE subscriptions SET status = 'canceled' WHERE tenant_id = :tid AND status IN ('active', 'trialing')"),
        {"tid": str(tenant_id)},
    )
    await db.execute(
        text("""
            INSERT INTO subscriptions (tenant_id, plan_id, provider, provider_customer_id, provider_subscription_id, status, current_period_start, current_period_end)
            VALUES (
                :tid,
                :plan_id,
                'mock_bypass',
                NULL,
                NULL,
                'active',
                now(),
                :current_period_end
            )
        """),
        {
            "tid": str(tenant_id),
            "plan_id": str(plan["id"]),
            "current_period_end": datetime.now(timezone.utc) + timedelta(days=365),
        },
    )
    await db.execute(
        text("UPDATE tenants SET plan = :plan_code, updated_at = now() WHERE id = :tid"),
        {"plan_code": plan_code, "tid": str(tenant_id)},
    )
    await log_audit(
        db,
        tenant_id=tenant_id,
        actor_user_id=user.id,
        action="subscription.change_internal",
        resource_type="subscription",
        resource_id=str(tenant_id),
        metadata={"plan_code": plan_code},
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()

    return {"message": "Plan changed successfully", "plan_code": plan_code}


# ── Execute PayPal Subscription ──
@router.post("/subscriptions/paypal/execute")
async def execute_paypal_subscription(
    token: str,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Execute PayPal subscription after user approval."""
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "settings.manage")

    # Get pending subscription details
    pending_result = await db.execute(
        text("""
            SELECT * FROM pending_subscriptions
            WHERE tenant_id = :tid
              AND (
                provider_agreement_id = :lookup_value
                OR metadata->>'paypal_token' = :lookup_value
              )
            ORDER BY created_at DESC LIMIT 1
        """),
        {"lookup_value": token, "tid": str(tenant_id)},
    )
    pending = pending_result.mappings().first()
    if not pending:
        raise HTTPException(status_code=404, detail="No pending subscription found")

    # Execute the PayPal subscription
    executed_sub = paypal_service.execute_subscription(token)
    if not executed_sub:
        raise HTTPException(status_code=500, detail="Failed to execute PayPal subscription")

    pending_meta = pending["metadata"] or {}
    billing_period = pending_meta.get("billing_period", "monthly")
    period_days = 365 if billing_period == "yearly" else 30
    current_period_end = datetime.now(timezone.utc) + timedelta(days=period_days)

    # Deactivate old active/trialing subscriptions
    await db.execute(
        text("UPDATE subscriptions SET status = 'canceled' WHERE tenant_id = :tid AND status IN ('active', 'trialing')"),
        {"tid": str(tenant_id)},
    )

    # Create new subscription in database
    await db.execute(
        text("""
            INSERT INTO subscriptions (tenant_id, plan_id, provider, provider_customer_id, provider_subscription_id, status, current_period_start, current_period_end)
            VALUES (
                :tid,
                :plan_id,
                'paypal',
                :payer_email,
                :subscription_id,
                'active',
                now(),
                :current_period_end
            )
        """),
        {
            "tid": str(tenant_id),
            "plan_id": str(pending["plan_id"]),
            "payer_email": executed_sub.get("payer_email", ""),
            "subscription_id": executed_sub["id"],
            "current_period_end": current_period_end,
        },
    )

    # Update tenant plan column
    await db.execute(
        text("UPDATE tenants SET plan = :plan_code, updated_at = now() WHERE id = :tid"),
        {"plan_code": pending_meta.get("plan_code", "starter"), "tid": str(tenant_id)}
    )

    # Delete pending subscription
    await db.execute(
        text("DELETE FROM pending_subscriptions WHERE id = :id"),
        {"id": str(pending["id"])},
    )

    await log_audit(
        db,
        tenant_id=tenant_id,
        actor_user_id=user.id,
        action="subscription.upgrade_paypal",
        resource_type="subscription",
        resource_id=str(tenant_id),
        metadata={
            "paypal_subscription_id": executed_sub["id"],
            "plan_code": pending_meta.get("plan_code"),
            "billing_period": billing_period,
        },
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()

    return {
        "message": "Subscription activated successfully",
        "subscription_id": executed_sub["id"],
        "plan_code": pending_meta.get("plan_code"),
        "billing_period": billing_period,
    }


# ── Cancel Subscription ──
@router.post("/subscriptions/cancel")
async def cancel_subscription(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel the current subscription at period end."""
    tenant_id = get_tenant_id_from_header(request)
    await require_owner(db, tenant_id, user.id)

    result = await db.execute(
        text("""
            SELECT id, provider, provider_subscription_id
            FROM subscriptions
            WHERE tenant_id = :tid AND status IN ('active', 'trialing')
            ORDER BY created_at DESC LIMIT 1
        """),
        {"tid": str(tenant_id)},
    )
    sub = result.mappings().first()
    if not sub:
        raise HTTPException(status_code=404, detail="No active subscription")

    # Cancel based on provider
    if sub["provider"] == "stripe" and sub["provider_subscription_id"]:
        # Cancel in Stripe
        stripe.Subscription.modify(
            sub["provider_subscription_id"],
            cancel_at_period_end=True,
        )
    elif sub["provider"] == "paypal" and sub["provider_subscription_id"]:
        # Cancel in PayPal
        canceled = paypal_service.cancel_subscription(sub["provider_subscription_id"])
        if not canceled:
            raise HTTPException(status_code=502, detail="Failed to cancel PayPal subscription")

    await db.execute(
        text("UPDATE subscriptions SET cancel_at_period_end = true WHERE id = :id"),
        {"id": str(sub["id"])},
    )

    await log_audit(
        db,
        tenant_id=tenant_id,
        actor_user_id=user.id,
        action="subscription.cancel",
        resource_type="subscription",
        resource_id=str(sub["id"]),
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()

    return {"message": "Subscription will be canceled at period end"}


# ══════════════════════════════════════════════
# PAYPAL WEBHOOKS
# ══════════════════════════════════════════════

@router.post("/webhooks/paypal", include_in_schema=False)
async def paypal_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle PayPal webhook events."""
    payload = await request.body()
    headers = dict(request.headers)

    # Verify webhook signature
    if not paypal_service.verify_webhook_signature(headers, payload.decode()):
        raise HTTPException(status_code=400, detail="Invalid signature")

    try:
        event_data = json.loads(payload.decode())
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid payload")

    event_type = event_data.get("event_type")
    resource = event_data.get("resource", {})

    # ── BILLING.SUBSCRIPTION.ACTIVATED ──
    if event_type == "BILLING.SUBSCRIPTION.ACTIVATED":
        subscription_id = resource.get("id")
        if subscription_id:
            await db.execute(
                text("""
                    UPDATE subscriptions
                    SET status = 'active'
                    WHERE provider_subscription_id = :sub_id AND provider = 'paypal'
                """),
                {"sub_id": subscription_id},
            )

    # ── BILLING.SUBSCRIPTION.CANCELLED ──
    elif event_type == "BILLING.SUBSCRIPTION.CANCELLED":
        subscription_id = resource.get("id")
        if subscription_id:
            # Get tenant_id before canceling
            sub_result = await db.execute(
                text("SELECT tenant_id FROM subscriptions WHERE provider_subscription_id = :sub_id AND provider = 'paypal'"),
                {"sub_id": subscription_id},
            )
            sub_row = sub_result.mappings().first()

            await db.execute(
                text("UPDATE subscriptions SET status = 'canceled' WHERE provider_subscription_id = :sub_id"),
                {"sub_id": subscription_id},
            )

            # Downgrade to free plan
            if sub_row:
                await db.execute(
                    text("""
                        INSERT INTO subscriptions (tenant_id, plan_id, provider, status, current_period_start, current_period_end)
                        VALUES (
                            :tid,
                            (SELECT id FROM plans WHERE code = 'starter'),
                            'mock_bypass',
                            'active',
                            now(),
                            now() + INTERVAL '30 days'
                        )
                    """),
                    {"tid": str(sub_row["tenant_id"])},
                )

    # ── PAYMENT.SALE.COMPLETED ──
    elif event_type == "PAYMENT.SALE.COMPLETED":
        # Payment successful - update subscription status if needed
        pass

    # ── PAYMENT.SALE.REFUNDED ──
    elif event_type == "PAYMENT.SALE.REFUNDED":
        # Handle refund if needed
        pass

    # ── Log the event ──
    provider_sub_id = resource.get("id") or resource.get("billing_agreement_id")
    if provider_sub_id:
        our_sub = await db.execute(
            text("SELECT id FROM subscriptions WHERE provider_subscription_id = :sub_id AND provider = 'paypal' ORDER BY created_at DESC LIMIT 1"),
            {"sub_id": provider_sub_id},
        )
        our_sub_row = our_sub.mappings().first()
        if our_sub_row:
            await db.execute(
                text("""
                    INSERT INTO subscription_events (subscription_id, event_type, provider_event_id, raw_payload)
                    VALUES (:sub_id, :event_type, :event_id, :payload::jsonb)
                """),
                {
                    "sub_id": str(our_sub_row["id"]),
                    "event_type": event_type,
                    "event_id": event_data.get("id"),
                    "payload": json.dumps(resource),
                },
            )

    await db.commit()
    return {"status": "ok"}


# ══════════════════════════════════════════════
# STRIPE WEBHOOKS (kept for backward compatibility)
# ══════════════════════════════════════════════

@router.post("/webhooks/stripe", include_in_schema=False)
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle Stripe webhook events."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event["type"]
    data = event["data"]["object"]

    # ── checkout.session.completed ──
    if event_type == "checkout.session.completed":
        tenant_id = data.get("metadata", {}).get("tenant_id")
        plan_code = data.get("metadata", {}).get("plan_code")
        customer_id = data.get("customer")
        subscription_id = data.get("subscription")

        if tenant_id and plan_code:
            # Deactivate old subscriptions
            await db.execute(
                text("UPDATE subscriptions SET status = 'canceled' WHERE tenant_id = :tid AND status IN ('active', 'trialing')"),
                {"tid": tenant_id},
            )

            # Create new subscription
            await db.execute(
                text("""
                    INSERT INTO subscriptions (tenant_id, plan_id, provider, provider_customer_id, provider_subscription_id, status, current_period_start, current_period_end)
                    VALUES (
                        :tid,
                        (SELECT id FROM plans WHERE code = :plan_code),
                        'stripe',
                        :customer_id,
                        :subscription_id,
                        'active',
                        now(),
                        now() + INTERVAL '30 days'
                    )
                """),
                {
                    "tid": tenant_id,
                    "plan_code": plan_code,
                    "customer_id": customer_id,
                    "subscription_id": subscription_id,
                },
            )

    # ── invoice.paid ──
    elif event_type == "invoice.paid":
        subscription_id = data.get("subscription")
        if subscription_id:
            period_end = data.get("lines", {}).get("data", [{}])[0].get("period", {}).get("end")
            if period_end:
                from datetime import datetime
                period_end_dt = datetime.fromtimestamp(period_end)
                await db.execute(
                    text("""
                        UPDATE subscriptions
                        SET status = 'active', current_period_end = :period_end
                        WHERE provider_subscription_id = :sub_id
                    """),
                    {"sub_id": subscription_id, "period_end": period_end_dt},
                )

    # ── invoice.payment_failed ──
    elif event_type == "invoice.payment_failed":
        subscription_id = data.get("subscription")
        if subscription_id:
            await db.execute(
                text("UPDATE subscriptions SET status = 'past_due' WHERE provider_subscription_id = :sub_id"),
                {"sub_id": subscription_id},
            )

    # ── customer.subscription.deleted ──
    elif event_type == "customer.subscription.deleted":
        subscription_id = data.get("id")
        if subscription_id:
            # Get tenant_id before canceling
            sub_result = await db.execute(
                text("SELECT tenant_id FROM subscriptions WHERE provider_subscription_id = :sub_id"),
                {"sub_id": subscription_id},
            )
            sub_row = sub_result.mappings().first()

            await db.execute(
                text("UPDATE subscriptions SET status = 'canceled' WHERE provider_subscription_id = :sub_id"),
                {"sub_id": subscription_id},
            )

            # Downgrade to free plan
            if sub_row:
                await db.execute(
                    text("""
                        INSERT INTO subscriptions (tenant_id, plan_id, status, current_period_start, current_period_end)
                        VALUES (
                            :tid,
                            (SELECT id FROM plans WHERE code = 'starter'),
                            'active',
                            now(),
                            now() + INTERVAL '30 days'
                        )
                    """),
                    {"tid": str(sub_row["tenant_id"])},
                )

    # ── Log the event ──
    # Find subscription in our DB
    provider_sub_id = data.get("subscription") or data.get("id")
    if provider_sub_id:
        our_sub = await db.execute(
            text("SELECT id FROM subscriptions WHERE provider_subscription_id = :sub_id ORDER BY created_at DESC LIMIT 1"),
            {"sub_id": provider_sub_id},
        )
        our_sub_row = our_sub.mappings().first()
        if our_sub_row:
            await db.execute(
                text("""
                    INSERT INTO subscription_events (subscription_id, event_type, provider_event_id, raw_payload)
                    VALUES (:sub_id, :event_type, :event_id, :payload::jsonb)
                """),
                {
                    "sub_id": str(our_sub_row["id"]),
                    "event_type": event_type,
                    "event_id": event.get("id"),
                    "payload": str(data),
                },
            )

    await db.commit()
    return {"status": "ok"}


# ══════════════════════════════════════════════
# CUSTOM PLAN BUILDER
# ══════════════════════════════════════════════

@router.get("/addons", response_model=list[PlanAddonRead])
async def list_addons(db: AsyncSession = Depends(get_db)):
    """List all available add-on items with pricing."""
    result = await db.execute(
        text("""
            SELECT id, key, label_ar, label_en, unit_ar, unit_en, icon,
                   min_value, max_value, step, price_per_unit,
                   category, sort_order, is_active
            FROM plan_addons
            WHERE is_active = true
            ORDER BY sort_order
        """)
    )
    rows = result.mappings().all()
    return [PlanAddonRead(**dict(r)) for r in rows]


async def _calculate_custom_plan(
    db: AsyncSession,
    body: CustomPlanRequest,
) -> CustomPlanCalculation:
    """
    Core calculation logic for custom plans.
    Takes a base plan + additional items, computes:
      - base price (from the chosen plan)
      - extra add-ons price (only for quantities ABOVE the plan's included limits)
      - final merged limits
    """
    # ── 1. Load base plan + its limits ──
    plan_result = await db.execute(
        text("""
            SELECT id, code, name, price_monthly, price_yearly
            FROM plans
            WHERE code = :code AND is_active = true
        """),
        {"code": body.base_plan_code},
    )
    base_plan = plan_result.mappings().first()
    if not base_plan:
        raise HTTPException(status_code=404, detail="الباقة الأساسية غير موجودة")

    limits_result = await db.execute(
        text("SELECT key, value FROM plan_limits WHERE plan_id = :pid"),
        {"pid": str(base_plan["id"])},
    )
    base_limits = {r["key"]: r["value"] for r in limits_result.mappings().all()}

    # ── 2. Load addon pricing ──
    addons_result = await db.execute(
        text("SELECT key, label_ar, label_en, icon, price_per_unit, step FROM plan_addons WHERE is_active = true")
    )
    addon_pricing = {r["key"]: dict(r) for r in addons_result.mappings().all()}

    # ── 3. Calculate each line item ──
    addon_lines: list[AddonLineItem] = []
    final_limits = dict(base_limits)
    addons_total = 0.0

    for item in body.items:
        if item.key not in addon_pricing:
            continue

        pricing = addon_pricing[item.key]
        base_value = base_limits.get(item.key, 0)
        # -1 means unlimited in base plan — no addon needed
        if base_value == -1:
            final_limits[item.key] = -1
            continue

        desired = item.quantity
        if desired <= base_value:
            # No extra needed, base plan already covers it
            final_limits[item.key] = base_value
            continue

        # Calculate extra units above base plan
        extra = desired - base_value
        step = pricing["step"]

        # Price per unit is per-step (e.g., 5 SAR per 100 invitations)
        if step > 1:
            # Round up to nearest step
            extra_steps = ceil(extra / step)
            line_total = round(extra_steps * float(pricing["price_per_unit"]), 2)
        else:
            line_total = round(extra * float(pricing["price_per_unit"]), 2)

        addons_total += line_total
        final_limits[item.key] = desired

        addon_lines.append(AddonLineItem(
            key=item.key,
            label_ar=pricing["label_ar"],
            label_en=pricing["label_en"],
            icon=pricing["icon"],
            base_value=base_value,
            extra_quantity=extra,
            unit_price=float(pricing["price_per_unit"]),
            line_total=line_total,
        ))

    base_price = float(base_plan["price_monthly"])
    total_monthly = round(base_price + addons_total, 2)

    # Enforce minimum price for paid custom plans
    if addons_total > 0 and total_monthly < CUSTOM_PLAN_MIN_PRICE:
        total_monthly = CUSTOM_PLAN_MIN_PRICE

    total_yearly = round(total_monthly * YEARLY_DISCOUNT_MONTHS, 2)

    return CustomPlanCalculation(
        base_plan_code=base_plan["code"],
        base_plan_name=base_plan["name"],
        base_price=base_price,
        addon_lines=addon_lines,
        addons_total=round(addons_total, 2),
        total_monthly=total_monthly,
        total_yearly=total_yearly,
        currency="SAR",
        final_limits=final_limits,
    )


@router.post("/custom-plans/calculate", response_model=CustomPlanCalculation)
async def calculate_custom_plan(
    body: CustomPlanRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Calculate the price for a custom plan without saving it.
    Use this for the live pricing preview in the UI.
    """
    return await _calculate_custom_plan(db, body)


@router.post("/custom-plans", response_model=CustomPlanRead, status_code=status.HTTP_201_CREATED)
async def create_custom_plan(
    body: CustomPlanRequest,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create and save a custom plan for the current tenant.
    This also creates the corresponding plan_limits entries.
    """
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "settings.manage")

    # Calculate pricing
    calc = await _calculate_custom_plan(db, body)

    # Get base plan ID
    plan_result = await db.execute(
        text("SELECT id FROM plans WHERE code = :code"),
        {"code": body.base_plan_code},
    )
    base_plan_row = plan_result.mappings().first()

    # Build addons dict for storage
    addons_dict = {item.key: item.quantity for item in body.items}

    # Insert custom plan
    result = await db.execute(
        text("""
            INSERT INTO custom_plans
                (tenant_id, base_plan_id, name, addons, base_price, addons_price,
                 total_price_monthly, total_price_yearly, final_limits, status, created_by)
            VALUES
                (:tid, :base_id, :name, :addons::jsonb, :base_price, :addons_price,
                 :total_monthly, :total_yearly, :final_limits::jsonb, 'active', :uid)
            RETURNING id, tenant_id, base_plan_id, name, addons, base_price, addons_price,
                      total_price_monthly, total_price_yearly, final_limits, status,
                      created_at, updated_at
        """),
        {
            "tid": str(tenant_id),
            "base_id": str(base_plan_row["id"]) if base_plan_row else None,
            "name": body.name or "باقتي المخصصة",
            "addons": json.dumps(addons_dict),
            "base_price": calc.base_price,
            "addons_price": calc.addons_total,
            "total_monthly": calc.total_monthly,
            "total_yearly": calc.total_yearly,
            "final_limits": json.dumps(calc.final_limits),
            "uid": str(user.id),
        },
    )
    row = result.mappings().first()

    # Deactivate any previous custom plans for this tenant
    await db.execute(
        text("""
            UPDATE custom_plans SET status = 'expired', updated_at = now()
            WHERE tenant_id = :tid AND id != :new_id AND status = 'active'
        """),
        {"tid": str(tenant_id), "new_id": str(row["id"])},
    )

    # Audit log
    await log_audit(
        db,
        tenant_id=tenant_id,
        actor_user_id=user.id,
        action="custom_plan.create",
        resource_type="custom_plan",
        resource_id=str(row["id"]),
        metadata={"base_plan": body.base_plan_code, "total": calc.total_monthly},
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()

    return CustomPlanRead(**dict(row))


@router.get("/custom-plans", response_model=list[CustomPlanRead])
async def list_custom_plans(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all custom plans for the current tenant."""
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "settings.manage")

    result = await db.execute(
        text("""
            SELECT id, tenant_id, base_plan_id, name, addons, base_price, addons_price,
                   total_price_monthly, total_price_yearly, final_limits, status,
                   created_at, updated_at
            FROM custom_plans
            WHERE tenant_id = :tid
            ORDER BY created_at DESC
        """),
        {"tid": str(tenant_id)},
    )
    rows = result.mappings().all()
    return [CustomPlanRead(**dict(r)) for r in rows]


@router.get("/custom-plans/active", response_model=CustomPlanRead)
async def get_active_custom_plan(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the active custom plan for the current tenant (if any)."""
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "settings.manage")

    result = await db.execute(
        text("""
            SELECT id, tenant_id, base_plan_id, name, addons, base_price, addons_price,
                   total_price_monthly, total_price_yearly, final_limits, status,
                   created_at, updated_at
            FROM custom_plans
            WHERE tenant_id = :tid AND status = 'active'
            ORDER BY created_at DESC
            LIMIT 1
        """),
        {"tid": str(tenant_id)},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="لا توجد باقة مخصصة نشطة")
    return CustomPlanRead(**dict(row))
