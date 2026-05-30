"""
Feature Gating Service.
Checks plan limits and feature flags before allowing actions.
"""
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
import logging

logger = logging.getLogger(__name__)


async def check_feature_flag(
    db: AsyncSession,
    tenant_id: UUID,
    flag_key: str,
) -> bool:
    """Check if a feature flag is enabled for a tenant."""
    result = await db.execute(
        text("SELECT enabled FROM feature_flags WHERE tenant_id = :tid AND flag_key = :key"),
        {"tid": str(tenant_id), "key": flag_key},
    )
    row = result.scalar()
    return bool(row)


async def require_feature(
    db: AsyncSession,
    tenant_id: UUID,
    flag_key: str,
) -> None:
    """Raise 403 if feature is not enabled for the tenant."""
    enabled = await check_feature_flag(db, tenant_id, flag_key)
    if not enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"الميزة '{flag_key}' غير مُفعّلة في خطتك الحالية.",
        )


async def get_plan_limit(
    db: AsyncSession,
    tenant_id: UUID,
    limit_key: str,
) -> int:
    """Get a specific plan limit value for a tenant. Returns -1 for unlimited."""
    result = await db.execute(
        text("""
            SELECT pl.value
            FROM plan_limits pl
            JOIN plans p ON p.id = pl.plan_id
            JOIN subscriptions s ON s.plan_id = p.id
            WHERE s.tenant_id = :tid
              AND s.status IN ('active', 'trialing')
              AND pl.key = :key
            ORDER BY s.created_at DESC
            LIMIT 1
        """),
        {"tid": str(tenant_id), "key": limit_key},
    )
    val = result.scalar()
    return val if val is not None else -1


async def check_limit(
    db: AsyncSession,
    tenant_id: UUID,
    limit_key: str,
    current_count: int,
) -> dict:
    """
    Check if a tenant has reached a specific limit.
    Returns dict with allowed, limit, current, remaining.
    """
    limit_value = await get_plan_limit(db, tenant_id, limit_key)

    if limit_value == -1:
        return {"allowed": True, "limit": -1, "current": current_count, "remaining": -1}

    remaining = max(0, limit_value - current_count)
    return {
        "allowed": current_count < limit_value,
        "limit": limit_value,
        "current": current_count,
        "remaining": remaining,
    }


async def require_within_limit(
    db: AsyncSession,
    tenant_id: UUID,
    limit_key: str,
    current_count: int,
    resource_name: str = "المورد",
) -> None:
    """Raise 429 if tenant has reached the limit."""
    result = await check_limit(db, tenant_id, limit_key, current_count)
    if not result["allowed"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"تم الوصول لحد {resource_name} ({result['limit']}). قم بترقية خطتك.",
        )


async def check_seats_limit(
    db: AsyncSession,
    tenant_id: UUID,
) -> None:
    """Check if tenant can add more members."""
    # Count current active members
    result = await db.execute(
        text("SELECT COUNT(*) FROM memberships WHERE tenant_id = :tid AND status = 'active'"),
        {"tid": str(tenant_id)},
    )
    current = result.scalar() or 0

    # Count pending invites
    pending = await db.execute(
        text("SELECT COUNT(*) FROM invites WHERE tenant_id = :tid AND status = 'pending'"),
        {"tid": str(tenant_id)},
    )
    pending_count = pending.scalar() or 0

    await require_within_limit(db, tenant_id, "seats_max", current + pending_count, "الأعضاء")


async def check_storage_limit(
    db: AsyncSession,
    tenant_id: UUID,
    current_mb: int,
) -> None:
    """Check if tenant can use more storage."""
    await require_within_limit(db, tenant_id, "storage_mb", current_mb, "التخزين")


async def get_tenant_limits_summary(
    db: AsyncSession,
    tenant_id: UUID,
) -> list[dict]:
    """Get all limits and current usage for a tenant."""
    result = await db.execute(
        text("""
            SELECT pl.key, pl.value AS limit_value, pl.period,
                   COALESCE(
                       (SELECT uc.value FROM usage_counters uc
                        WHERE uc.tenant_id = :tid AND uc.key = pl.key
                        AND uc.period_start = date_trunc('month', CURRENT_DATE)::DATE
                        LIMIT 1),
                       0
                   ) AS current_usage
            FROM plan_limits pl
            JOIN plans p ON p.id = pl.plan_id
            JOIN subscriptions s ON s.plan_id = p.id
            WHERE s.tenant_id = :tid AND s.status IN ('active', 'trialing')
            ORDER BY pl.key
        """),
        {"tid": str(tenant_id)},
    )
    rows = result.mappings().all()

    summary = []
    for r in rows:
        limit_val = r["limit_value"]
        current = r["current_usage"]
        # For seats, count from memberships instead of usage_counters
        if r["key"] == "seats_max":
            seats_result = await db.execute(
                text("SELECT COUNT(*) FROM memberships WHERE tenant_id = :tid AND status = 'active'"),
                {"tid": str(tenant_id)},
            )
            current = seats_result.scalar() or 0

        remaining = max(0, limit_val - current) if limit_val != -1 else -1
        summary.append({
            "key": r["key"],
            "limit": limit_val,
            "current": current,
            "remaining": remaining,
            "period": r["period"],
            "exceeded": current >= limit_val if limit_val != -1 else False,
        })

    return summary
