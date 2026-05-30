from uuid import UUID
from datetime import date
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models.usage import UsageLimitInfo, UsageCheckResult


async def get_tenant_plan_limits(db: AsyncSession, tenant_id: UUID) -> tuple[str, list[dict]]:
    """Get the active plan and its limits for a tenant."""
    result = await db.execute(
        text("""
            SELECT p.code AS plan_code, pl.key, pl.value, pl.period
            FROM subscriptions s
            JOIN plans p ON p.id = s.plan_id
            JOIN plan_limits pl ON pl.plan_id = p.id
            WHERE s.tenant_id = :tenant_id
              AND s.status IN ('active', 'trialing')
            ORDER BY s.created_at DESC
            LIMIT 100
        """),
        {"tenant_id": str(tenant_id)},
    )
    rows = result.mappings().all()

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="No active subscription found for this tenant",
        )

    plan_code = rows[0]["plan_code"]
    limits = [dict(r) for r in rows]
    return plan_code, limits


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

    for limit in limits:
        key = limit["key"]
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
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Usage limit exceeded for '{usage_key}'. "
                       f"Current: {current}, Limit: {limit_value}, Requested: {amount}",
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
