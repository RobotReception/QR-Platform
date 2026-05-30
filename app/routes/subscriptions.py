import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, Header, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.auth import get_current_user, get_tenant_id_from_header, CurrentUser
from app.config import get_settings
from app.database import get_db
from app.models.subscription import SubscriptionRead, SubscriptionWithPlan
from app.models.plan import PlanRead, PlanWithLimits, PlanLimitRead
from app.services.membership_service import require_admin, require_owner
from app.services.audit_service import log_audit

settings = get_settings()
stripe.api_key = settings.stripe_secret_key

router = APIRouter(tags=["Subscriptions & Plans"])


# ══════════════════════════════════════════════
# PLANS (public)
# ══════════════════════════════════════════════

@router.get("/plans", response_model=list[PlanWithLimits])
async def list_plans(db: AsyncSession = Depends(get_db)):
    """List all active plans with their limits."""
    try:
        plans_result = await db.execute(
            text("SELECT id, code, name, price_monthly, price_yearly, currency, is_active, sort_order FROM plans WHERE is_active = true ORDER BY sort_order")
        )
        plans = plans_result.mappings().all()

        result = []
        for plan in plans:
            limits_result = await db.execute(
                text("SELECT id, plan_id, key, value, period FROM plan_limits WHERE plan_id = :pid"),
                {"pid": str(plan["id"])},
            )
            limits = [PlanLimitRead(**dict(l)) for l in limits_result.mappings().all()]
            result.append(PlanWithLimits(**dict(plan), limits=limits))
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
                'USD' AS currency,
                true AS is_active,
                row_number() OVER (ORDER BY price_monthly, name)::int AS sort_order
            FROM plans
            ORDER BY price_monthly, name
        """)
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
    await require_admin(db, tenant_id, user.id)

    result = await db.execute(
        text("""
            SELECT s.*, p.code AS plan_code, p.name AS plan_name
            FROM subscriptions s
            JOIN plans p ON p.id = s.plan_id
            WHERE s.tenant_id = :tid AND s.status IN ('active', 'trialing')
            ORDER BY s.created_at DESC
            LIMIT 1
        """),
        {"tid": str(tenant_id)},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="No active subscription")
    return SubscriptionWithPlan(**dict(row))


# ── Create Stripe Checkout Session ──
@router.post("/subscriptions/checkout")
async def create_checkout_session(
    plan_code: str,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a Stripe Checkout session for upgrading/changing plan."""
    tenant_id = get_tenant_id_from_header(request)
    await require_admin(db, tenant_id, user.id)

    # Get plan
    plan_result = await db.execute(
        text("SELECT id, code, name, price_monthly FROM plans WHERE code = :code AND is_active = true"),
        {"code": plan_code},
    )
    plan = plan_result.mappings().first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    # Get or create Stripe customer
    sub_result = await db.execute(
        text("SELECT provider_customer_id FROM subscriptions WHERE tenant_id = :tid ORDER BY created_at DESC LIMIT 1"),
        {"tid": str(tenant_id)},
    )
    sub_row = sub_result.mappings().first()
    customer_id = sub_row["provider_customer_id"] if sub_row and sub_row["provider_customer_id"] else None

    if not customer_id:
        customer = stripe.Customer.create(
            email=user.email,
            metadata={"tenant_id": str(tenant_id)},
        )
        customer_id = customer.id

    # Create checkout session
    # NOTE: In production, you'd use Stripe Price IDs instead of ad-hoc prices
    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {"name": plan["name"]},
                "unit_amount": int(plan["price_monthly"] * 100),
                "recurring": {"interval": "month"},
            },
            "quantity": 1,
        }],
        metadata={
            "tenant_id": str(tenant_id),
            "plan_code": plan_code,
        },
        success_url=f"{settings.app_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.app_url}/billing/cancel",
    )

    return {"checkout_url": session.url, "session_id": session.id}


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
            SELECT id, provider_subscription_id
            FROM subscriptions
            WHERE tenant_id = :tid AND status IN ('active', 'trialing')
            ORDER BY created_at DESC LIMIT 1
        """),
        {"tid": str(tenant_id)},
    )
    sub = result.mappings().first()
    if not sub:
        raise HTTPException(status_code=404, detail="No active subscription")

    if sub["provider_subscription_id"]:
        # Cancel in Stripe
        stripe.Subscription.modify(
            sub["provider_subscription_id"],
            cancel_at_period_end=True,
        )

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
# STRIPE WEBHOOKS
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
                            (SELECT id FROM plans WHERE code = 'free'),
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
