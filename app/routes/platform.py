"""
Platform Admin Routes.
Only accessible by users with is_staff=true (super admins).
Manages all tenants across the platform.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional
from pydantic import BaseModel

from app.auth import get_current_user, CurrentUser
from app.database import get_db
from app.models.tenant import TenantRead
from app.services.audit_service import log_audit

router = APIRouter(prefix="/platform", tags=["Platform Admin"])


# ── Staff check dependency ──
async def require_staff(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    """Ensure the user is a platform admin (is_staff=true)."""
    result = await db.execute(
        text("SELECT is_staff FROM profiles WHERE id = :uid"),
        {"uid": str(user.id)},
    )
    row = result.mappings().first()
    if not row or not row["is_staff"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="هذا الإجراء مخصص لمشرفي المنصة فقط",
        )
    return user


class PlatformTenantRead(BaseModel):
    id: UUID
    slug: str
    name: str
    status: str
    plan: str
    created_by: Optional[UUID] = None
    metadata: Optional[dict] = None
    expires_at: Optional[str] = None
    created_at: str
    updated_at: str
    members_count: Optional[int] = None


class TenantStatusUpdate(BaseModel):
    status: str  # active, suspended, cancelled


# ── List All Tenants ──
@router.get("/tenants", response_model=list[PlatformTenantRead])
async def list_all_tenants(
    status_filter: Optional[str] = Query(None, alias="status"),
    plan: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List all tenants on the platform. Staff only."""
    query = """
        SELECT t.id, t.slug, t.name, t.status, t.plan, t.created_by,
               t.metadata, t.expires_at::text, t.created_at::text, t.updated_at::text,
               (SELECT COUNT(*) FROM memberships m WHERE m.tenant_id = t.id AND m.status = 'active') AS members_count
        FROM tenants t
        WHERE 1=1
    """
    params: dict = {"limit": limit, "offset": offset}

    if status_filter:
        query += " AND t.status = :status"
        params["status"] = status_filter

    if plan:
        query += " AND t.plan = :plan"
        params["plan"] = plan

    if search:
        query += " AND (t.name ILIKE :search OR t.slug ILIKE :search)"
        params["search"] = f"%{search}%"

    query += " ORDER BY t.created_at DESC LIMIT :limit OFFSET :offset"

    result = await db.execute(text(query), params)
    rows = result.mappings().all()
    return [PlatformTenantRead(**dict(r)) for r in rows]


# ── Get Tenant Details ──
@router.get("/tenants/{tenant_id}", response_model=PlatformTenantRead)
async def get_tenant_detail(
    tenant_id: UUID,
    user: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed info about a specific tenant. Staff only."""
    result = await db.execute(
        text("""
            SELECT t.id, t.slug, t.name, t.status, t.plan, t.created_by,
                   t.metadata, t.expires_at::text, t.created_at::text, t.updated_at::text,
                   (SELECT COUNT(*) FROM memberships m WHERE m.tenant_id = t.id AND m.status = 'active') AS members_count
            FROM tenants t WHERE t.id = :tid
        """),
        {"tid": str(tenant_id)},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="المستأجر غير موجود")
    return PlatformTenantRead(**dict(row))


# ── Suspend Tenant ──
@router.post("/tenants/{tenant_id}/suspend")
async def suspend_tenant(
    tenant_id: UUID,
    request: Request,
    user: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Suspend a tenant. All users lose access. Staff only."""
    result = await db.execute(
        text("UPDATE tenants SET status = 'suspended', updated_at = now() WHERE id = :tid AND status != 'suspended' RETURNING id"),
        {"tid": str(tenant_id)},
    )
    if not result.first():
        raise HTTPException(status_code=404, detail="المستأجر غير موجود أو معلّق مسبقاً")

    await log_audit(
        db, tenant_id=tenant_id, actor_user_id=user.id,
        action="tenant.suspend", resource_type="tenant", resource_id=str(tenant_id),
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    return {"message": "تم تعليق المستأجر بنجاح"}


# ── Activate Tenant ──
@router.post("/tenants/{tenant_id}/activate")
async def activate_tenant(
    tenant_id: UUID,
    request: Request,
    user: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Re-activate a suspended or cancelled tenant. Staff only."""
    result = await db.execute(
        text("UPDATE tenants SET status = 'active', updated_at = now() WHERE id = :tid AND status IN ('suspended', 'cancelled') RETURNING id"),
        {"tid": str(tenant_id)},
    )
    if not result.first():
        raise HTTPException(status_code=404, detail="المستأجر غير موجود أو نشط مسبقاً")

    await log_audit(
        db, tenant_id=tenant_id, actor_user_id=user.id,
        action="tenant.activate", resource_type="tenant", resource_id=str(tenant_id),
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    return {"message": "تم تفعيل المستأجر بنجاح"}


# ── Cancel Tenant ──
@router.post("/tenants/{tenant_id}/cancel")
async def cancel_tenant(
    tenant_id: UUID,
    request: Request,
    user: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a tenant permanently. Staff only."""
    result = await db.execute(
        text("UPDATE tenants SET status = 'cancelled', updated_at = now() WHERE id = :tid AND status != 'cancelled' RETURNING id"),
        {"tid": str(tenant_id)},
    )
    if not result.first():
        raise HTTPException(status_code=404, detail="المستأجر غير موجود أو ملغى مسبقاً")

    await log_audit(
        db, tenant_id=tenant_id, actor_user_id=user.id,
        action="tenant.cancel", resource_type="tenant", resource_id=str(tenant_id),
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    return {"message": "تم إلغاء المستأجر"}


# ── Platform Stats ──
@router.get("/stats")
async def platform_stats(
    user: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get platform-wide statistics. Staff only."""
    result = await db.execute(text("""
        SELECT
            (SELECT COUNT(*) FROM tenants) AS total_tenants,
            (SELECT COUNT(*) FROM tenants WHERE status = 'active') AS active_tenants,
            (SELECT COUNT(*) FROM tenants WHERE status = 'trial') AS trial_tenants,
            (SELECT COUNT(*) FROM tenants WHERE status = 'suspended') AS suspended_tenants,
            (SELECT COUNT(*) FROM profiles) AS total_users,
            (SELECT COUNT(*) FROM memberships WHERE status = 'active') AS total_memberships,
            (SELECT COUNT(*) FROM subscriptions WHERE status = 'active') AS active_subscriptions
    """))
    row = result.mappings().first()
    return dict(row)
