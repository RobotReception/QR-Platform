"""
Platform Admin Routes — Super Admin Dashboard.
Only accessible by users with is_staff=true (super admins).
Full platform management: tenants, users, plans, subscriptions, analytics.
"""
import json
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
from app.services.staff_service import require_staff
from app.routes.roles import PermissionRead, RoleRead, RoleCreate, RoleUpdate

router = APIRouter(prefix="/platform", tags=["Platform Admin"])


async def _safe(db, sql, params=None):
    """Run a query safely, returning None on error."""
    try:
        return await db.execute(text(sql), params or {})
    except Exception:
        await db.rollback()
        return None


# ══════════════════════════════════════════════════
# MODELS
# ══════════════════════════════════════════════════

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


class PlanUpdate(BaseModel):
    name: Optional[str] = None
    subtitle: Optional[str] = None
    description: Optional[str] = None
    price_monthly: Optional[float] = None
    price_yearly: Optional[float] = None
    is_active: Optional[bool] = None
    is_popular: Optional[bool] = None
    badge_color: Optional[str] = None


class PlanLimitItem(BaseModel):
    key: str
    value: int
    period: str = "none"


class AddonUpdate(BaseModel):
    label_ar: Optional[str] = None
    label_en: Optional[str] = None
    unit_ar: Optional[str] = None
    unit_en: Optional[str] = None
    icon: Optional[str] = None
    price_per_unit: Optional[float] = None
    is_active: Optional[bool] = None


# ══════════════════════════════════════════════════
# COMPREHENSIVE ANALYTICS
# ══════════════════════════════════════════════════

@router.get("/analytics")
async def platform_analytics(
    user: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Comprehensive platform analytics for super admin dashboard."""
    analytics = {}

    # ── KPIs ──
    r = await _safe(db, """
        SELECT
            (SELECT COUNT(*) FROM tenants) AS total_tenants,
            (SELECT COUNT(*) FROM tenants WHERE status = 'active') AS active_tenants,
            (SELECT COUNT(*) FROM tenants WHERE status = 'trial') AS trial_tenants,
            (SELECT COUNT(*) FROM tenants WHERE status = 'suspended') AS suspended_tenants,
            (SELECT COUNT(*) FROM tenants WHERE status = 'cancelled') AS cancelled_tenants,
            (SELECT COUNT(*) FROM tenants WHERE created_at >= CURRENT_DATE - INTERVAL '30 days') AS new_tenants_30d,
            (SELECT COUNT(*) FROM tenants WHERE created_at >= CURRENT_DATE - INTERVAL '7 days') AS new_tenants_7d,
            (SELECT COUNT(*) FROM profiles) AS total_users,
            (SELECT COUNT(*) FROM profiles WHERE created_at >= CURRENT_DATE - INTERVAL '30 days') AS new_users_30d,
            (SELECT COUNT(*) FROM memberships WHERE status = 'active') AS total_active_memberships,
            (SELECT COUNT(*) FROM subscriptions WHERE status = 'active') AS active_subscriptions,
            (SELECT COUNT(*) FROM events) AS total_events,
            (SELECT COUNT(*) FROM invitations) AS total_invitations,
            (SELECT COUNT(*) FROM guests) AS total_guests
    """)
    if r:
        analytics["kpis"] = dict(r.mappings().first())
    else:
        analytics["kpis"] = {}

    # ── Revenue (MRR / ARR) ──
    r = await _safe(db, """
        SELECT
            COALESCE(SUM(p.price_monthly), 0) AS mrr,
            COALESCE(SUM(p.price_monthly * 12), 0) AS arr,
            COALESCE(AVG(p.price_monthly), 0) AS avg_revenue_per_tenant,
            COUNT(*) AS paying_count
        FROM subscriptions s
        JOIN plans p ON p.id = s.plan_id
        WHERE s.status = 'active' AND p.price_monthly > 0
    """)
    if r:
        row = r.mappings().first()
        analytics["revenue"] = {
            "mrr": float(row["mrr"]),
            "arr": float(row["arr"]),
            "avg_revenue_per_tenant": round(float(row["avg_revenue_per_tenant"]), 2),
            "paying_tenants": row["paying_count"],
        }
    else:
        analytics["revenue"] = {"mrr": 0, "arr": 0, "avg_revenue_per_tenant": 0, "paying_tenants": 0}

    # ── Plan distribution ──
    r = await _safe(db, """
        SELECT p.code AS plan, p.name AS plan_name, p.badge_color, COUNT(s.id) AS count
        FROM plans p
        LEFT JOIN subscriptions s ON s.plan_id = p.id AND s.status = 'active'
        GROUP BY p.code, p.name, p.badge_color, p.sort_order
        ORDER BY p.sort_order
    """)
    if r:
        analytics["plan_distribution"] = [dict(row) for row in r.mappings().all()]
    else:
        analytics["plan_distribution"] = []

    # ── Status distribution ──
    r = await _safe(db, """
        SELECT status, COUNT(*) AS count
        FROM tenants
        GROUP BY status
        ORDER BY count DESC
    """)
    if r:
        analytics["status_distribution"] = [dict(row) for row in r.mappings().all()]
    else:
        analytics["status_distribution"] = []

    # ── Trend (last 30 days) ──
    r = await _safe(db, """
        SELECT d::date AS date,
               COALESCE(t.cnt, 0) AS new_tenants,
               COALESCE(u.cnt, 0) AS new_users
        FROM generate_series(CURRENT_DATE - 29, CURRENT_DATE, '1 day') d
        LEFT JOIN (
            SELECT created_at::date AS d, COUNT(*) AS cnt FROM tenants
            WHERE created_at >= CURRENT_DATE - 29
            GROUP BY created_at::date
        ) t ON t.d = d.d
        LEFT JOIN (
            SELECT created_at::date AS d, COUNT(*) AS cnt FROM profiles
            WHERE created_at >= CURRENT_DATE - 29
            GROUP BY created_at::date
        ) u ON u.d = d.d
        ORDER BY d
    """)
    if r:
        analytics["trend_30d"] = [
            {"date": str(row["date"]), "new_tenants": row["new_tenants"], "new_users": row["new_users"]}
            for row in r.mappings().all()
        ]
    else:
        analytics["trend_30d"] = []

    # ── Recent tenants ──
    r = await _safe(db, """
        SELECT t.id::text, t.slug, t.name, t.status, t.plan,
               t.created_at::text,
               (SELECT COUNT(*) FROM memberships m WHERE m.tenant_id = t.id AND m.status = 'active') AS members_count
        FROM tenants t
        ORDER BY t.created_at DESC
        LIMIT 10
    """)
    if r:
        analytics["recent_tenants"] = [dict(row) for row in r.mappings().all()]
    else:
        analytics["recent_tenants"] = []

    # ── Top tenants by activity ──
    r = await _safe(db, """
        SELECT t.id::text, t.slug, t.name, t.plan,
               (SELECT COUNT(*) FROM events e WHERE e.tenant_id = t.id) AS events_count,
               (SELECT COUNT(*) FROM invitations i WHERE i.tenant_id = t.id) AS invitations_count,
               (SELECT COUNT(*) FROM memberships m WHERE m.tenant_id = t.id AND m.status = 'active') AS members_count
        FROM tenants t
        WHERE t.status = 'active'
        ORDER BY invitations_count DESC
        LIMIT 10
    """)
    if r:
        analytics["top_tenants"] = [dict(row) for row in r.mappings().all()]
    else:
        analytics["top_tenants"] = []

    return analytics


# ══════════════════════════════════════════════════
# TENANTS MANAGEMENT
# ══════════════════════════════════════════════════

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


@router.get("/tenants/{tenant_id}")
async def get_tenant_detail(
    tenant_id: UUID,
    user: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed info about a specific tenant. Staff only."""
    # Tenant info
    result = await db.execute(
        text("""
            SELECT t.id::text, t.slug, t.name, t.status, t.plan, t.created_by::text,
                   t.metadata, t.expires_at::text, t.created_at::text, t.updated_at::text,
                   (SELECT COUNT(*) FROM memberships m WHERE m.tenant_id = t.id AND m.status = 'active') AS members_count,
                   (SELECT COUNT(*) FROM events e WHERE e.tenant_id = t.id) AS events_count,
                   (SELECT COUNT(*) FROM invitations i WHERE i.tenant_id = t.id) AS invitations_count,
                   (SELECT COUNT(*) FROM guests g WHERE g.tenant_id = t.id) AS guests_count
            FROM tenants t WHERE t.id = :tid
        """),
        {"tid": str(tenant_id)},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="المستأجر غير موجود")

    # Subscription info
    sub_result = await db.execute(
        text("""
            SELECT s.status::text AS sub_status, p.code AS plan_code, p.name AS plan_name,
                   p.price_monthly, s.current_period_end::text, s.trial_ends_at::text
            FROM subscriptions s JOIN plans p ON p.id = s.plan_id
            WHERE s.tenant_id = :tid ORDER BY s.created_at DESC LIMIT 1
        """),
        {"tid": str(tenant_id)},
    )
    sub = sub_result.mappings().first()

    # Members
    members_result = await db.execute(
        text("""
            SELECT p.id::text AS user_id, p.full_name, p.avatar_url,
                   m.role::text, m.status::text, m.created_at::text
            FROM memberships m JOIN profiles p ON p.id = m.user_id
            WHERE m.tenant_id = :tid ORDER BY m.created_at
        """),
        {"tid": str(tenant_id)},
    )

    return {
        "tenant": dict(row),
        "subscription": dict(sub) if sub else None,
        "members": [dict(r) for r in members_result.mappings().all()],
    }


@router.post("/tenants/{tenant_id}/suspend")
async def suspend_tenant(
    tenant_id: UUID, request: Request,
    user: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Suspend a tenant. Staff only."""
    result = await db.execute(
        text("UPDATE tenants SET status = 'suspended', updated_at = now() WHERE id = :tid AND status != 'suspended' RETURNING id"),
        {"tid": str(tenant_id)},
    )
    if not result.first():
        raise HTTPException(status_code=404, detail="المستأجر غير موجود أو معلّق مسبقاً")
    await log_audit(db, tenant_id=tenant_id, actor_user_id=user.id,
                    action="tenant.suspend", resource_type="tenant", resource_id=str(tenant_id),
                    ip_address=request.client.host if request.client else None)
    await db.commit()
    return {"message": "تم تعليق المستأجر بنجاح", "status": "suspended"}


@router.post("/tenants/{tenant_id}/activate")
async def activate_tenant(
    tenant_id: UUID, request: Request,
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
    await log_audit(db, tenant_id=tenant_id, actor_user_id=user.id,
                    action="tenant.activate", resource_type="tenant", resource_id=str(tenant_id),
                    ip_address=request.client.host if request.client else None)
    await db.commit()
    return {"message": "تم تفعيل المستأجر بنجاح", "status": "active"}


@router.post("/tenants/{tenant_id}/cancel")
async def cancel_tenant(
    tenant_id: UUID, request: Request,
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
    await log_audit(db, tenant_id=tenant_id, actor_user_id=user.id,
                    action="tenant.cancel", resource_type="tenant", resource_id=str(tenant_id),
                    ip_address=request.client.host if request.client else None)
    await db.commit()
    return {"message": "تم إلغاء المستأجر", "status": "cancelled"}


# ══════════════════════════════════════════════════
# USERS MANAGEMENT
# ══════════════════════════════════════════════════

@router.get("/users")
async def list_all_users(
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List all users on the platform. Staff only."""
    query = """
        SELECT p.id::text, p.full_name, p.avatar_url, p.is_staff,
               p.created_at::text, p.last_login_at::text,
               (SELECT COUNT(*) FROM memberships m WHERE m.user_id = p.id AND m.status = 'active') AS tenants_count,
               (SELECT au.email FROM auth.users au WHERE au.id = p.id) AS email
        FROM profiles p
        WHERE 1=1
    """
    params: dict = {"limit": limit, "offset": offset}

    if search:
        query += " AND (p.full_name ILIKE :search OR EXISTS (SELECT 1 FROM auth.users au WHERE au.id = p.id AND au.email ILIKE :search))"
        params["search"] = f"%{search}%"

    query += " ORDER BY p.created_at DESC LIMIT :limit OFFSET :offset"
    result = await db.execute(text(query), params)
    rows = result.mappings().all()

    # Total count
    count_query = "SELECT COUNT(*) FROM profiles"
    count_result = await db.execute(text(count_query))
    total = count_result.scalar()

    return {"users": [dict(r) for r in rows], "total": total}


@router.get("/users/{user_id}")
async def get_user_detail(
    user_id: UUID,
    user: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get user detail with all their tenant memberships."""
    result = await db.execute(
        text("""
            SELECT p.id::text, p.full_name, p.avatar_url, p.is_staff,
                   p.created_at::text, p.last_login_at::text,
                   (SELECT au.email FROM auth.users au WHERE au.id = p.id) AS email
            FROM profiles p WHERE p.id = :uid
        """),
        {"uid": str(user_id)},
    )
    profile = result.mappings().first()
    if not profile:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    # Get all memberships
    memberships_result = await db.execute(
        text("""
            SELECT t.id::text AS tenant_id, t.name AS tenant_name, t.slug,
                   m.role::text, m.status::text, m.created_at::text
            FROM memberships m JOIN tenants t ON t.id = m.tenant_id
            WHERE m.user_id = :uid ORDER BY m.created_at
        """),
        {"uid": str(user_id)},
    )

    return {
        "user": dict(profile),
        "memberships": [dict(r) for r in memberships_result.mappings().all()],
    }


# ══════════════════════════════════════════════════
# SUBSCRIPTIONS & REVENUE
# ══════════════════════════════════════════════════

@router.get("/subscriptions")
async def list_all_subscriptions(
    status_filter: Optional[str] = Query(None, alias="status"),
    plan_code: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List all subscriptions across the platform."""
    query = """
        SELECT s.id::text, s.tenant_id::text, t.name AS tenant_name, t.slug AS tenant_slug,
               s.status::text AS sub_status, p.code AS plan_code, p.name AS plan_name,
               p.price_monthly, s.current_period_start::text, s.current_period_end::text,
               s.trial_ends_at::text, s.created_at::text
        FROM subscriptions s
        JOIN plans p ON p.id = s.plan_id
        JOIN tenants t ON t.id = s.tenant_id
        WHERE 1=1
    """
    params: dict = {"limit": limit, "offset": offset}

    if status_filter:
        query += " AND s.status = :status"
        params["status"] = status_filter

    if plan_code:
        query += " AND p.code = :plan_code"
        params["plan_code"] = plan_code

    query += " ORDER BY s.created_at DESC LIMIT :limit OFFSET :offset"
    result = await db.execute(text(query), params)
    return [dict(r) for r in result.mappings().all()]


# ══════════════════════════════════════════════════
# AUDIT LOGS (Platform-wide)
# ══════════════════════════════════════════════════

@router.get("/audit-logs")
async def list_audit_logs(
    action: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List audit logs across the entire platform."""
    query = """
        SELECT a.id::text, a.tenant_id::text, t.name AS tenant_name,
               a.actor_user_id::text, p.full_name AS actor_name,
               a.action, a.resource_type, a.resource_id,
               a.metadata, a.ip_address::text, a.created_at::text
        FROM audit_logs a
        LEFT JOIN tenants t ON t.id = a.tenant_id
        LEFT JOIN profiles p ON p.id = a.actor_user_id
        WHERE 1=1
    """
    params: dict = {"limit": limit, "offset": offset}

    if action:
        query += " AND a.action ILIKE :action"
        params["action"] = f"%{action}%"

    if tenant_id:
        query += " AND a.tenant_id = :tid"
        params["tid"] = tenant_id

    query += " ORDER BY a.created_at DESC LIMIT :limit OFFSET :offset"
    result = await db.execute(text(query), params)
    return [dict(r) for r in result.mappings().all()]


# ══════════════════════════════════════════════════
# PLANS MANAGEMENT
# ══════════════════════════════════════════════════

@router.get("/plans-overview")
async def plans_overview(
    user: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get all plans with subscriber counts and addon pricing."""
    # Plans with counts
    plans_result = await db.execute(text("""
        SELECT p.id::text, p.code, p.name, p.description, p.subtitle,
               p.price_monthly, p.price_yearly, p.currency,
               p.badge_color, p.is_popular, p.is_active, p.sort_order,
               COUNT(s.id) FILTER (WHERE s.status = 'active') AS active_subscribers,
               COUNT(s.id) AS total_subscribers
        FROM plans p
        LEFT JOIN subscriptions s ON s.plan_id = p.id
        GROUP BY p.id
        ORDER BY p.sort_order
    """))
    plans = [dict(r) for r in plans_result.mappings().all()]

    # Addons
    addons_result = await db.execute(text("""
        SELECT id::text, key, label_ar, label_en, unit_ar, icon,
               price_per_unit, step, category, sort_order
        FROM plan_addons WHERE is_active = true ORDER BY sort_order
    """))
    addons = [dict(r) for r in addons_result.mappings().all()]

    # Custom plans count
    custom_result = await db.execute(text("""
        SELECT COUNT(*) FILTER (WHERE status = 'active') AS active_custom,
               COUNT(*) AS total_custom
        FROM custom_plans
    """))
    custom = dict(custom_result.mappings().first())

    return {"plans": plans, "addons": addons, "custom_plans": custom}


# ── Platform Stats (legacy, kept for backward compatibility) ──
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


# ── Update Plan, Limits, and Addons ──

@router.patch("/plans/{plan_id}")
async def update_plan(
    plan_id: UUID,
    body: PlanUpdate,
    user: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Update general plan details. Staff only."""
    updates = []
    params = {"pid": str(plan_id)}
    
    for field, val in body.dict(exclude_unset=True).items():
        updates.append(f"{field} = :{field}")
        params[field] = val
        
    if not updates:
        raise HTTPException(status_code=400, detail="لا توجد بيانات لتحديثها")
        
    query = f"UPDATE plans SET {', '.join(updates)}, updated_at = now() WHERE id = :pid"
    await db.execute(text(query), params)
    await db.commit()
    
    # Log audit
    await log_audit(
        db,
        tenant_id=None,
        actor_user_id=user.id,
        action="plan.update",
        resource_type="plan",
        resource_id=str(plan_id),
        metadata={"updated_fields": list(body.dict(exclude_unset=True).keys())}
    )
    return {"message": "تم تحديث الباقة بنجاح"}


@router.get("/plans/{plan_id}/limits")
async def get_plan_limits(
    plan_id: UUID,
    user: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get all limits for a specific plan. Staff only."""
    result = await db.execute(
        text("SELECT key, value, period FROM plan_limits WHERE plan_id = :pid"),
        {"pid": str(plan_id)}
    )
    return [dict(r) for r in result.mappings().all()]


@router.put("/plans/{plan_id}/limits")
async def update_plan_limits(
    plan_id: UUID,
    limits: list[PlanLimitItem],
    user: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Update all limits for a specific plan. Staff only."""
    # Delete existing limits
    await db.execute(text("DELETE FROM plan_limits WHERE plan_id = :pid"), {"pid": str(plan_id)})
    
    # Insert new limits
    for limit in limits:
        await db.execute(
            text("INSERT INTO plan_limits (plan_id, key, value, period) VALUES (:pid, :key, :val, :per)"),
            {"pid": str(plan_id), "key": limit.key, "val": limit.value, "per": limit.period}
        )
    await db.commit()
    
    # Log audit
    await log_audit(
        db,
        tenant_id=None,
        actor_user_id=user.id,
        action="plan.limits_update",
        resource_type="plan",
        resource_id=str(plan_id),
        metadata={"limits_count": len(limits)}
    )
    return {"message": "تم تحديث حدود الباقة بنجاح"}


@router.patch("/addons/{addon_id}")
async def update_addon(
    addon_id: UUID,
    body: AddonUpdate,
    user: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Update plan addon details. Staff only."""
    updates = []
    params = {"aid": str(addon_id)}
    
    for field, val in body.dict(exclude_unset=True).items():
        updates.append(f"{field} = :{field}")
        params[field] = val
        
    if not updates:
        raise HTTPException(status_code=400, detail="لا توجد بيانات لتحديثها")
        
    query = f"UPDATE plan_addons SET {', '.join(updates)} WHERE id = :aid"
    await db.execute(text(query), params)
    await db.commit()
    
    # Log audit
    await log_audit(
        db,
        tenant_id=None,
        actor_user_id=user.id,
        action="addon.update",
        resource_type="addon",
        resource_id=str(addon_id),
        metadata={"updated_fields": list(body.dict(exclude_unset=True).keys())}
    )
    return {"message": "تم تحديث الميزة الإضافية بنجاح"}


# ══════════════════════════════════════════════════
# ROLES & PERMISSIONS (Platform staff only)
# ══════════════════════════════════════════════════

async def _tenant_exists(db: AsyncSession, tenant_id: UUID) -> None:
    row = await db.execute(
        text("SELECT 1 FROM tenants WHERE id = :tid"),
        {"tid": str(tenant_id)},
    )
    if not row.first():
        raise HTTPException(status_code=404, detail="المؤسسة غير موجودة")


@router.get("/permissions", response_model=list[PermissionRead])
async def platform_list_permissions(
    user: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List all system permissions. Platform staff only."""
    result = await db.execute(
        text("SELECT key, description FROM permissions ORDER BY key")
    )
    return [PermissionRead(**dict(r)) for r in result.mappings().all()]


@router.get("/tenants/{tenant_id}/roles", response_model=list[RoleRead])
async def platform_list_tenant_roles(
    tenant_id: UUID,
    user: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List roles and permissions for a tenant. Platform staff only."""
    await _tenant_exists(db, tenant_id)
    result = await db.execute(
        text("""
            SELECT r.id, r.tenant_id, r.name, r.description, r.is_system_role,
                   r.created_at::text,
                   ARRAY(
                       SELECT rp.permission_key FROM role_permissions rp WHERE rp.role_id = r.id
                   ) AS permissions
            FROM roles r
            WHERE r.tenant_id = :tid
            ORDER BY r.is_system_role DESC, r.name
        """),
        {"tid": str(tenant_id)},
    )
    return [RoleRead(**dict(r)) for r in result.mappings().all()]


@router.post("/tenants/{tenant_id}/roles", response_model=RoleRead, status_code=status.HTTP_201_CREATED)
async def platform_create_role(
    tenant_id: UUID,
    body: RoleCreate,
    request: Request,
    user: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a custom role for a tenant. Platform staff only."""
    await _tenant_exists(db, tenant_id)

    existing = await db.execute(
        text("SELECT 1 FROM roles WHERE tenant_id = :tid AND name = :name"),
        {"tid": str(tenant_id), "name": body.name},
    )
    if existing.first():
        raise HTTPException(status_code=409, detail="يوجد دور بنفس الاسم")

    if body.permissions:
        valid = await db.execute(
            text("SELECT key FROM permissions WHERE key = ANY(:keys)"),
            {"keys": body.permissions},
        )
        valid_keys = {r[0] for r in valid.fetchall()}
        invalid = set(body.permissions) - valid_keys
        if invalid:
            raise HTTPException(status_code=400, detail=f"صلاحيات غير موجودة: {', '.join(invalid)}")

    result = await db.execute(
        text("""
            INSERT INTO roles (tenant_id, name, description, is_system_role)
            VALUES (:tid, :name, :desc, false)
            RETURNING id, tenant_id, name, description, is_system_role, created_at::text
        """),
        {"tid": str(tenant_id), "name": body.name, "desc": body.description},
    )
    role = result.mappings().first()

    for pkey in body.permissions:
        await db.execute(
            text("INSERT INTO role_permissions (role_id, permission_key) VALUES (:rid, :pkey)"),
            {"rid": str(role["id"]), "pkey": pkey},
        )

    await log_audit(
        db, tenant_id=tenant_id, actor_user_id=user.id,
        action="platform.role.create", resource_type="role", resource_id=str(role["id"]),
        metadata={"name": body.name, "permissions": body.permissions},
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    return RoleRead(**dict(role), permissions=body.permissions)


@router.patch("/tenants/{tenant_id}/roles/{role_id}", response_model=RoleRead)
async def platform_update_role(
    tenant_id: UUID,
    role_id: UUID,
    body: RoleUpdate,
    request: Request,
    user: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Update role permissions for a tenant. Platform staff only."""
    await _tenant_exists(db, tenant_id)

    existing = await db.execute(
        text("SELECT id, is_system_role FROM roles WHERE id = :rid AND tenant_id = :tid"),
        {"rid": str(role_id), "tid": str(tenant_id)},
    )
    role_row = existing.mappings().first()
    if not role_row:
        raise HTTPException(status_code=404, detail="الدور غير موجود")
    is_system = role_row["is_system_role"]

    updates = body.model_dump(exclude_unset=True, exclude={"permissions"})
    if updates:
        if is_system:
            raise HTTPException(status_code=403, detail="لا يمكن تعديل اسم أو وصف الأدوار النظامية")
        set_clauses = ", ".join(f"{k} = :{k}" for k in updates)
        updates["rid"] = str(role_id)
        await db.execute(text(f"UPDATE roles SET {set_clauses} WHERE id = :rid"), updates)

    if body.permissions is not None:
        if body.permissions:
            valid = await db.execute(
                text("SELECT key FROM permissions WHERE key = ANY(:keys)"),
                {"keys": body.permissions},
            )
            valid_keys = {r[0] for r in valid.fetchall()}
            invalid = set(body.permissions) - valid_keys
            if invalid:
                raise HTTPException(status_code=400, detail=f"صلاحيات غير موجودة: {', '.join(invalid)}")

        await db.execute(
            text("DELETE FROM role_permissions WHERE role_id = :rid"),
            {"rid": str(role_id)},
        )
        for pkey in body.permissions:
            await db.execute(
                text("INSERT INTO role_permissions (role_id, permission_key) VALUES (:rid, :pkey)"),
                {"rid": str(role_id), "pkey": pkey},
            )

    await log_audit(
        db, tenant_id=tenant_id, actor_user_id=user.id,
        action="platform.role.update", resource_type="role", resource_id=str(role_id),
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()

    result = await db.execute(
        text("""
            SELECT r.id, r.tenant_id, r.name, r.description, r.is_system_role,
                   r.created_at::text,
                   ARRAY(SELECT rp.permission_key FROM role_permissions rp WHERE rp.role_id = r.id) AS permissions
            FROM roles r WHERE r.id = :rid
        """),
        {"rid": str(role_id)},
    )
    return RoleRead(**dict(result.mappings().first()))


@router.delete("/tenants/{tenant_id}/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def platform_delete_role(
    tenant_id: UUID,
    role_id: UUID,
    request: Request,
    user: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Delete a custom role. Platform staff only."""
    await _tenant_exists(db, tenant_id)

    existing = await db.execute(
        text("SELECT id, is_system_role FROM roles WHERE id = :rid AND tenant_id = :tid"),
        {"rid": str(role_id), "tid": str(tenant_id)},
    )
    role_row = existing.mappings().first()
    if not role_row:
        raise HTTPException(status_code=404, detail="الدور غير موجود")
    if role_row["is_system_role"]:
        raise HTTPException(status_code=403, detail="لا يمكن حذف الأدوار النظامية")

    assigned = await db.execute(
        text("SELECT 1 FROM membership_roles WHERE role_id = :rid LIMIT 1"),
        {"rid": str(role_id)},
    )
    if assigned.first():
        raise HTTPException(status_code=409, detail="لا يمكن حذف دور مُسند لأعضاء. قم بإزالة الدور من الأعضاء أولاً.")

    await db.execute(text("DELETE FROM roles WHERE id = :rid"), {"rid": str(role_id)})

    await log_audit(
        db, tenant_id=tenant_id, actor_user_id=user.id,
        action="platform.role.delete", resource_type="role", resource_id=str(role_id),
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
