from uuid import UUID
from datetime import date
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models.usage import UsageLimitInfo, UsageCheckResult


async def get_tenant_plan_limits(db: AsyncSession, tenant_id: UUID) -> tuple[str, list[dict]]:
    """Get the active plan and its limits for a tenant."""
    # 1. Check active custom plan first
    custom_res = await db.execute(
        text("""
            SELECT cp.base_plan_id, p.code AS plan_code, cp.final_limits
            FROM custom_plans cp
            JOIN plans p ON p.id = cp.base_plan_id
            WHERE cp.tenant_id = :tenant_id AND cp.status = 'active'
            LIMIT 1
        """),
        {"tenant_id": str(tenant_id)},
    )
    custom_row = custom_res.mappings().first()
    if custom_row:
        plan_code = custom_row["plan_code"]
        final_limits = custom_row["final_limits"] or {}
        # Fetch base plan limits
        base_limits_res = await db.execute(
            text("""
                SELECT pl.key, pl.value, pl.period
                FROM plan_limits pl
                WHERE pl.plan_id = :plan_id
                LIMIT 100
            """),
            {"plan_id": custom_row["base_plan_id"]},
        )
        base_limits = {r["key"]: dict(r) for r in base_limits_res.mappings().all()}
        
        # Override with custom plan limits
        for k, v in final_limits.items():
            if k in base_limits:
                base_limits[k]["value"] = v
            else:
                base_limits[k] = {"key": k, "value": v, "period": "month" if "month" in k else "none"}
                
        # Return in the expected list of dict format
        limits_list = [{"plan_code": plan_code, **item} for item in base_limits.values()]
        return plan_code, limits_list

    # 2. Check standard subscription plan limits
    latest_sub_res = await db.execute(
        text("""
            SELECT s.plan_id, p.code AS plan_code
            FROM subscriptions s
            JOIN plans p ON p.id = s.plan_id
            WHERE s.tenant_id = :tenant_id
              AND s.status IN ('active', 'trialing')
            ORDER BY s.created_at DESC
            LIMIT 1
        """),
        {"tenant_id": str(tenant_id)},
    )
    latest_sub = latest_sub_res.mappings().first()
    if latest_sub:
        limits_res = await db.execute(
            text("""
                SELECT :plan_code AS plan_code, pl.key, pl.value, pl.period
                FROM plan_limits pl
                WHERE pl.plan_id = :plan_id
                ORDER BY pl.key
                LIMIT 100
            """),
            {"plan_id": str(latest_sub["plan_id"]), "plan_code": latest_sub["plan_code"]},
        )
        plan_code = latest_sub["plan_code"]
        limits = [dict(r) for r in limits_res.mappings().all()]
        return plan_code, limits

    # 3. Fallback: Check limits associated with the plan code in tenants table
    tenant_res = await db.execute(
        text("SELECT plan FROM tenants WHERE id = :tenant_id"),
        {"tenant_id": str(tenant_id)},
    )
    tenant_row = tenant_res.mappings().first()
    plan_code = tenant_row["plan"] if tenant_row else None
    if not plan_code:
        plan_code = "starter"

    fallback_limits_res = await db.execute(
        text("""
            SELECT p.code AS plan_code, pl.key, pl.value, pl.period
            FROM plan_limits pl
            JOIN plans p ON p.id = pl.plan_id
            WHERE LOWER(p.code) = LOWER(:plan_code)
            LIMIT 100
        """),
        {"plan_code": plan_code},
    )
    rows = fallback_limits_res.mappings().all()
    if rows:
        return plan_code, [dict(r) for r in rows]

    # 4. Ultimate fallback to starter
    ultimate_limits_res = await db.execute(
        text("""
            SELECT p.code AS plan_code, pl.key, pl.value, pl.period
            FROM plan_limits pl
            JOIN plans p ON p.id = pl.plan_id
            WHERE LOWER(p.code) = 'starter'
            LIMIT 100
        """),
    )
    rows = ultimate_limits_res.mappings().all()
    if rows:
        return "starter", [dict(r) for r in rows]

    raise HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail="No active subscription or valid plans found for this tenant",
    )


async def get_current_usage(db: AsyncSession, tenant_id: UUID) -> dict[str, int]:
    """Get current month's usage counters for a tenant."""
    period_start = date.today().replace(day=1)

    result = await db.execute(
        text("""
            SELECT key, value
            FROM usage_counters
            WHERE tenant_id = :tenant_id
              AND period_start = :period_start
        """),
        {"tenant_id": str(tenant_id), "period_start": period_start},
    )
    rows = result.mappings().all()
    return {r["key"]: r["value"] for r in rows}


async def check_all_limits(db: AsyncSession, tenant_id: UUID) -> UsageCheckResult:
    """Check all usage limits for a tenant."""
    plan_code, limits = await get_tenant_plan_limits(db, tenant_id)
    usage = await get_current_usage(db, tenant_id)

    limit_infos = []
    any_exceeded = False
    seen_keys: set[str] = set()

    for limit in limits:
        key = limit["key"]
        if key in seen_keys:
            continue
        seen_keys.add(key)
        max_value = limit["value"]
        current = usage.get(key, 0)

        # -1 means unlimited
        if max_value == -1:
            remaining = -1
            is_exceeded = False
        else:
            remaining = max(0, max_value - current)
            is_exceeded = current >= max_value

        if is_exceeded:
            any_exceeded = True

        limit_infos.append(
            UsageLimitInfo(
                key=key,
                limit=max_value,
                current_usage=current,
                remaining=remaining,
                is_exceeded=is_exceeded,
            )
        )

    return UsageCheckResult(
        tenant_id=tenant_id,
        plan_code=plan_code,
        limits=limit_infos,
        any_exceeded=any_exceeded,
    )


async def check_and_increment(
    db: AsyncSession,
    tenant_id: UUID,
    usage_key: str,
    amount: int = 1,
) -> int:
    """
    Check if tenant can consume the resource, then atomically increment.
    Returns the new usage value.
    Raises 429 if limit exceeded.
    """
    plan_code, limits = await get_tenant_plan_limits(db, tenant_id)

    # Find the relevant limit
    limit_value = None
    for limit in limits:
        if limit["key"] == usage_key:
            limit_value = limit["value"]
            break

    if limit_value is None:
        # No limit defined for this key — allow
        pass
    elif limit_value != -1:
        # Check current usage
        usage = await get_current_usage(db, tenant_id)
        current = usage.get(usage_key, 0)
        if current + amount > limit_value:
            RESOURCE_NAMES_AR = {
                "events_per_month": "الفعاليات شهرياً",
                "invitations_per_month": "الدعوات شهرياً",
                "gates_per_event": "البوابات لكل حدث",
                "teams_max": "فرق العمل",
                "seats_max": "المستخدمين في المنصة",
                "designed_templates": "القوالب المصممة",
                "guests_max": "الضيوف",
                "invitations_per_event": "الدعوات لكل حدث",
                "messages_per_month": "الرسائل الشهرية",
                "registration_forms_max": "نماذج التسجيل النشطة",
                "storage_mb": "التخزين",
            }
            res_name = RESOURCE_NAMES_AR.get(usage_key, usage_key)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"تم تجاوز الحد الأقصى لـ '{res_name}'. "
                       f"الحالي: {current}، المسموح به: {limit_value}، المطلوب: {amount}."
            )

    # Atomically increment
    result = await db.execute(
        text("SELECT public.increment_usage(:tenant_id, :key, :amount)"),
        {"tenant_id": str(tenant_id), "key": usage_key, "amount": amount},
    )
    new_value = result.scalar()
    await db.commit()
    return new_value


async def get_seats_count(db: AsyncSession, tenant_id: UUID) -> int:
    """Count active members in a tenant."""
    result = await db.execute(
        text("""
            SELECT COUNT(*) FROM memberships
            WHERE tenant_id = :tenant_id AND status = 'active'
        """),
        {"tenant_id": str(tenant_id)},
    )
    return result.scalar() or 0
