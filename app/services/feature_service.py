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
    # 1. Check explicit override in feature_flags table
    result = await db.execute(
        text("SELECT enabled FROM feature_flags WHERE tenant_id = :tid AND flag_key = :key"),
        {"tid": str(tenant_id), "key": flag_key},
    )
    row = result.scalar()
    if row is not None:
        return bool(row)

    # 2. Dynamic resolution based on plan code hierarchy
    plan_code = None
    # Check if there is an active custom plan (which overrides standard plan features)
    custom_res = await db.execute(
        text("""
            SELECT p.code
            FROM custom_plans cp
            JOIN plans p ON p.id = cp.base_plan_id
            WHERE cp.tenant_id = :tid AND cp.status = 'active'
            LIMIT 1
        """),
        {"tid": str(tenant_id)},
    )
    plan_code = custom_res.scalar()

    if not plan_code:
        # Check standard active subscription
        sub_res = await db.execute(
            text("""
                SELECT p.code
                FROM plans p
                JOIN subscriptions s ON s.plan_id = p.id
                WHERE s.tenant_id = :tid
                  AND s.status IN ('active', 'trialing')
                ORDER BY s.created_at DESC
                LIMIT 1
            """),
            {"tid": str(tenant_id)},
        )
        plan_code = sub_res.scalar()

    if not plan_code:
        # Fallback to plan code in tenants table
        tenant_res = await db.execute(
            text("SELECT plan FROM tenants WHERE id = :tid"),
            {"tid": str(tenant_id)},
        )
        plan_code = tenant_res.scalar() or "starter"

    # Normalize plan code to lowercase
    plan_code = plan_code.lower() if plan_code else "starter"

    # Hierarchy-based feature gates
    if flag_key == "email_delivery":
        return True  # all plans can send emails
    elif flag_key == "rsvp":
        return plan_code in ("basic", "pro", "business", "enterprise")
    elif flag_key in ("whatsapp_delivery", "pdf_export", "ai_features"):
        return plan_code in ("pro", "business", "enterprise")

    # Default to False for other features unless explicitly enabled in feature_flags
    return False


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
            detail=f"الميزة '{flag_key}' غير مُفعّلة في خطتك الحالية. يرجى ترقية خطتك.",
        )


async def get_plan_limit(
    db: AsyncSession,
    tenant_id: UUID,
    limit_key: str,
) -> int:
    """Get a specific plan limit value for a tenant. Returns -1 for unlimited."""
    # 1. Check active custom plan override first
    custom_res = await db.execute(
        text("SELECT final_limits FROM custom_plans WHERE tenant_id = :tid AND status = 'active' LIMIT 1"),
        {"tid": str(tenant_id)},
    )
    custom_row = custom_res.scalar()
    if custom_row and isinstance(custom_row, dict) and limit_key in custom_row:
        return int(custom_row[limit_key])

    # 2. Check standard subscription plan limits
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
    if val is not None:
        return val

    # 3. Fallback: Check limits associated with the plan code in tenants table
    tenant_res = await db.execute(
        text("""
            SELECT pl.value
            FROM plan_limits pl
            JOIN plans p ON p.id = pl.plan_id
            JOIN tenants t ON LOWER(t.plan) = LOWER(p.code)
            WHERE t.id = :tid AND pl.key = :key
            LIMIT 1
        """),
        {"tid": str(tenant_id), "key": limit_key},
    )
    fallback_val = tenant_res.scalar()
    return fallback_val if fallback_val is not None else -1


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


async def get_tenant_storage_bytes(db: AsyncSession, tenant_id: UUID) -> int:
    """Sum tracked storage: template assets + non-asset uploads (event covers, etc.)."""
    assets_res = await db.execute(
        text("""
            SELECT COALESCE(SUM(ta.file_size), 0)
            FROM template_assets ta
            JOIN invite_templates it ON it.id = ta.template_id
            WHERE it.tenant_id = :tid
        """),
        {"tid": str(tenant_id)},
    )
    assets_bytes = int(assets_res.scalar() or 0)

    extra_res = await db.execute(
        text("""
            SELECT COALESCE(value, 0)
            FROM usage_counters
            WHERE tenant_id = :tid AND key = 'storage_bytes'
              AND period_start = '1970-01-01'::date
        """),
        {"tid": str(tenant_id)},
    )
    extra_bytes = int(extra_res.scalar() or 0)
    return assets_bytes + extra_bytes


async def require_storage_for_upload(
    db: AsyncSession,
    tenant_id: UUID,
    file_size_bytes: int,
) -> None:
    """Raise 429 if uploading file_size_bytes would exceed the tenant storage_mb plan limit."""
    current_bytes = await get_tenant_storage_bytes(db, tenant_id)
    projected_mb = (current_bytes + file_size_bytes + 1024 * 1024 - 1) // (1024 * 1024)
    await check_storage_limit(db, tenant_id, projected_mb)


async def record_non_asset_storage(
    db: AsyncSession,
    tenant_id: UUID,
    file_size_bytes: int,
) -> None:
    """Track storage used by uploads not stored in template_assets (e.g. event covers)."""
    if file_size_bytes <= 0:
        return
    await db.execute(
        text("""
            INSERT INTO usage_counters (tenant_id, period_start, period_end, key, value)
            VALUES (:tid, '1970-01-01'::date, '2099-12-31'::date, 'storage_bytes', :val)
            ON CONFLICT (tenant_id, period_start, key)
            DO UPDATE SET value = usage_counters.value + :val, updated_at = now()
        """),
        {"tid": str(tenant_id), "val": file_size_bytes},
    )


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



async def enforce_monthly_limit(
    db: AsyncSession,
    tenant_id: UUID,
    limit_key: str,
    resource_name: str,
    count: int = 1,
) -> None:
    """
    Check a monthly usage counter against plan limit.
    Uses usage_service.check_and_increment to atomically verify and increment.
    Raises 429 if limit exceeded.
    """
    from app.services.usage_service import check_and_increment
    await check_and_increment(db, tenant_id, limit_key, count)


async def enforce_static_limit(
    db: AsyncSession,
    tenant_id: UUID,
    limit_key: str,
    current_count: int,
    resource_name: str,
    requested: int = 1,
) -> None:
    """
    Check a static (non-monthly) limit against current count.
    Raises 429 if adding 'requested' items would exceed the plan limit.
    """
    limit_value = await get_plan_limit(db, tenant_id, limit_key)
    if limit_value == -1:
        return  # unlimited
    if current_count + requested > limit_value:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"تم الوصول لحد {resource_name} ({limit_value}). "
                   f"الحالي: {current_count}، المطلوب: {requested}. قم بترقية خطتك.",
        )

