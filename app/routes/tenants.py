from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from datetime import datetime, timezone
from pydantic import BaseModel as PydanticBaseModel

from app.auth import get_current_user, get_tenant_id_from_header, CurrentUser
from app.database import get_db
from app.models.tenant import TenantCreate, TenantRead, TenantUpdate, TenantSettingRead, TenantSettingWrite, TenantDomainRead, TenantDomainCreate
import json
from app.models.membership import MembershipRead, MemberWithProfile, MembershipUpdate
from app.services.membership_service import verify_membership, require_admin, require_owner
from app.services.audit_service import log_audit
from app.services.provisioning_service import provision_tenant_manual
from app.services.permission_service import require_permission

router = APIRouter(prefix="/tenants", tags=["Tenants"])


# ── Create Tenant ──
@router.post("", response_model=TenantRead, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    body: TenantCreate,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new tenant and assign the creator as owner."""
    # Check slug uniqueness
    existing = await db.execute(
        text("SELECT id FROM tenants WHERE slug = :slug"),
        {"slug": body.slug},
    )
    if existing.first():
        raise HTTPException(status_code=409, detail="Slug already taken")

    # Create tenant
    result = await db.execute(
        text("""
            INSERT INTO tenants (slug, name, created_by, metadata)
            VALUES (:slug, :name, :created_by, :metadata::jsonb)
            RETURNING id, slug, name, created_by, status, plan, metadata, expires_at, created_at, updated_at
        """),
        {
            "slug": body.slug,
            "name": body.name,
            "created_by": str(user.id),
            "metadata": json.dumps(body.metadata or {}, default=str),
        },
    )
    tenant = result.mappings().first()

    # Create owner membership
    await db.execute(
        text("""
            INSERT INTO memberships (tenant_id, user_id, role, status)
            VALUES (:tenant_id, :user_id, 'owner', 'active')
        """),
        {"tenant_id": str(tenant["id"]), "user_id": str(user.id)},
    )

    # Create free trial subscription
    await db.execute(
        text("""
            INSERT INTO subscriptions (tenant_id, plan_id, status, current_period_start, current_period_end, trial_ends_at)
            VALUES (
                :tenant_id,
                (SELECT id FROM plans WHERE code = 'free'),
                'active',
                now(),
                now() + INTERVAL '30 days',
                now() + INTERVAL '14 days'
            )
        """),
        {"tenant_id": str(tenant["id"])},
    )

    # Provision: create default roles, permissions, settings
    await provision_tenant_manual(db, tenant["id"], user.id)

    # Audit log
    await log_audit(
        db,
        tenant_id=tenant["id"],
        actor_user_id=user.id,
        action="tenant.create",
        resource_type="tenant",
        resource_id=str(tenant["id"]),
        ip_address=request.client.host if request.client else None,
    )

    await db.commit()
    return TenantRead(**dict(tenant))


# ── List My Tenants ──
@router.get("", response_model=list[TenantRead])
async def list_my_tenants(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all tenants the current user belongs to."""
    result = await db.execute(
        text("""
            SELECT t.id, t.slug, t.name, t.created_by, t.status, t.plan, t.metadata, t.expires_at,
                   t.created_at, t.updated_at
            FROM tenants t
            JOIN memberships m ON m.tenant_id = t.id
            WHERE m.user_id = :user_id AND m.status = 'active'
            ORDER BY t.created_at DESC
        """),
        {"user_id": str(user.id)},
    )
    rows = result.mappings().all()
    return [TenantRead(**dict(r)) for r in rows]


# ── Get Tenant Details ──
@router.get("/current", response_model=TenantRead)
async def get_current_tenant(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get details of the current tenant (from X-Tenant-ID header)."""
    tenant_id = get_tenant_id_from_header(request)
    await verify_membership(db, tenant_id, user.id)

    result = await db.execute(
        text("SELECT id, slug, name, created_by, status, plan, metadata, expires_at, created_at, updated_at FROM tenants WHERE id = :id"),
        {"id": str(tenant_id)},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return TenantRead(**dict(row))


# ── Update Tenant ──
@router.patch("/current", response_model=TenantRead)
async def update_tenant(
    body: TenantUpdate,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update tenant details. Requires admin role."""
    tenant_id = get_tenant_id_from_header(request)
    await require_admin(db, tenant_id, user.id)

    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clauses = ", ".join(f"{k} = :{k}" for k in updates)
    updates["id"] = str(tenant_id)

    result = await db.execute(
        text(f"""
            UPDATE tenants SET {set_clauses}, updated_at = now()
            WHERE id = :id
            RETURNING id, slug, name, created_by, status, plan, metadata, expires_at, created_at, updated_at
        """),
        updates,
    )
    row = result.mappings().first()

    await log_audit(
        db,
        tenant_id=tenant_id,
        actor_user_id=user.id,
        action="tenant.update",
        resource_type="tenant",
        resource_id=str(tenant_id),
        metadata=updates,
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    return TenantRead(**dict(row))


# ── List Members ──
@router.get("/current/members", response_model=list[MemberWithProfile])
async def list_members(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all members of the current tenant with their profiles."""
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "members.view")

    result = await db.execute(
        text("""
            SELECT m.tenant_id, m.user_id, m.role, m.status, m.created_at,
                   p.full_name, p.avatar_url
            FROM memberships m
            JOIN profiles p ON p.id = m.user_id
            WHERE m.tenant_id = :tenant_id
            ORDER BY m.created_at
        """),
        {"tenant_id": str(tenant_id)},
    )
    rows = result.mappings().all()
    return [MemberWithProfile(**dict(r)) for r in rows]


# ── Update Member Role ──
@router.patch("/current/members/{member_id}", response_model=MembershipRead)
async def update_member(
    member_id: UUID,
    body: MembershipUpdate,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a member's role or status. Requires members.manage permission."""
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "members.manage")

    # Cannot change own role
    if member_id == user.id:
        raise HTTPException(status_code=400, detail="Cannot change your own role")

    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clauses = ", ".join(f"{k} = :{k}" for k in updates)
    updates["tenant_id"] = str(tenant_id)
    updates["user_id"] = str(member_id)

    result = await db.execute(
        text(f"""
            UPDATE memberships SET {set_clauses}, updated_at = now()
            WHERE tenant_id = :tenant_id AND user_id = :user_id
            RETURNING tenant_id, user_id, role, status, created_at, updated_at
        """),
        updates,
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Member not found")

    await log_audit(
        db,
        tenant_id=tenant_id,
        actor_user_id=user.id,
        action="member.update",
        resource_type="membership",
        resource_id=str(member_id),
        metadata=updates,
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    return MembershipRead(**dict(row))


# ── Create Member (Admin) ──
class CreateMemberRequest(PydanticBaseModel):
    email: str
    full_name: str = ""
    password: str
    role: str = "member"


@router.post("/current/members", response_model=MemberWithProfile, status_code=status.HTTP_201_CREATED)
async def create_member(
    body: CreateMemberRequest,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new user and add them to the current tenant. Requires members.manage."""
    from app.database import get_supabase_admin, get_supabase_client

    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "members.manage")

    # Validate role
    if body.role not in ("admin", "member", "viewer"):
        raise HTTPException(status_code=400, detail="الدور غير صالح")

    # Check if already a member
    existing = await db.execute(
        text("""
            SELECT 1 FROM memberships m
            JOIN profiles p ON p.id = m.user_id
            WHERE m.tenant_id = :tid
              AND p.id IN (SELECT au.id FROM auth.users au WHERE au.email = :email)
        """),
        {"tid": str(tenant_id), "email": body.email},
    )
    if existing.first():
        raise HTTPException(status_code=409, detail="المستخدم عضو بالفعل في هذه المؤسسة")

    new_user_id: str = ""

    # Try 1: Use Supabase Admin API (requires SERVICE_ROLE_KEY)
    try:
        supabase_admin = get_supabase_admin()
        result = supabase_admin.auth.admin.create_user({
            "email": body.email,
            "password": body.password,
            "email_confirm": True,
            "user_metadata": {"full_name": body.full_name},
        })
        if result and result.user:
            new_user_id = str(result.user.id)
    except Exception as admin_error:
        # Admin API failed, try fallback method
        print(f"Admin API failed: {admin_error}")

        # Try 2: Use sign_up (public API) - user will need email confirmation
        try:
            supabase_client = get_supabase_client()
            result = supabase_client.auth.sign_up({
                "email": body.email,
                "password": body.password,
                "options": {
                    "data": {"full_name": body.full_name or ""}
                }
            })
            if result and result.user:
                new_user_id = str(result.user.id)
        except Exception as signup_error:
            print(f"Sign up failed: {signup_error}")

            # Try 3: User might already exist - find them
            try:
                find_result = await db.execute(
                    text("SELECT id FROM auth.users WHERE email = :email"),
                    {"email": body.email},
                )
                found = find_result.mappings().first()
                if found:
                    new_user_id = str(found["id"])
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"فشل إنشاء المستخدم. تأكد من إعدادات Supabase."
                    )
            except Exception as find_error:
                raise HTTPException(
                    status_code=400,
                    detail=f"فشل إنشاء المستخدم: {str(find_error)}"
                )

    if not new_user_id:
        raise HTTPException(status_code=400, detail="فشل إنشاء المستخدم")

    # Ensure profile exists
    await db.execute(
        text("""
            INSERT INTO profiles (id, full_name, avatar_url)
            VALUES (:uid, :name, '')
            ON CONFLICT (id) DO UPDATE SET full_name = COALESCE(NULLIF(:name, ''), profiles.full_name)
        """),
        {"uid": new_user_id, "name": body.full_name},
    )

    # Create membership
    await db.execute(
        text("""
            INSERT INTO memberships (tenant_id, user_id, role, status)
            VALUES (:tid, :uid, :role, 'active')
            ON CONFLICT (tenant_id, user_id) DO UPDATE SET role = :role, status = 'active'
        """),
        {"tid": str(tenant_id), "uid": new_user_id, "role": body.role},
    )

    await log_audit(
        db, tenant_id=tenant_id, actor_user_id=user.id,
        action="member.create", resource_type="membership",
        resource_id=new_user_id,
        metadata={"email": body.email, "role": body.role},
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()

    return MemberWithProfile(
        tenant_id=tenant_id,
        user_id=new_user_id,
        role=body.role,
        status="active",
        created_at=datetime.now(timezone.utc),
        full_name=body.full_name,
        avatar_url=None,
    )


# ── Remove Member ──
@router.delete("/current/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    member_id: UUID,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a member from the tenant. Requires members.manage permission."""
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "members.manage")

    if member_id == user.id:
        raise HTTPException(status_code=400, detail="Cannot remove yourself")

    result = await db.execute(
        text("DELETE FROM memberships WHERE tenant_id = :tenant_id AND user_id = :user_id"),
        {"tenant_id": str(tenant_id), "user_id": str(member_id)},
    )

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Member not found")

    await log_audit(
        db,
        tenant_id=tenant_id,
        actor_user_id=user.id,
        action="member.remove",
        resource_type="membership",
        resource_id=str(member_id),
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()


# ── Tenant Settings ──
@router.get("/current/settings", response_model=list[TenantSettingRead])
async def list_settings(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "settings.view")

    result = await db.execute(
        text("SELECT tenant_id, key, value, updated_at FROM tenant_settings WHERE tenant_id = :tid"),
        {"tid": str(tenant_id)},
    )
    rows = result.mappings().all()
    return [TenantSettingRead(**dict(r)) for r in rows]


@router.put("/current/settings", response_model=TenantSettingRead)
async def upsert_setting(
    body: TenantSettingWrite,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "settings.manage")

    result = await db.execute(
        text("""
            INSERT INTO tenant_settings (tenant_id, key, value)
            VALUES (:tid, :key, :value::jsonb)
            ON CONFLICT (tenant_id, key)
            DO UPDATE SET value = :value::jsonb, updated_at = now()
            RETURNING tenant_id, key, value, updated_at
        """),
        {"tid": str(tenant_id), "key": body.key, "value": str(body.value)},
    )
    row = result.mappings().first()
    await db.commit()
    return TenantSettingRead(**dict(row))


# ══════════════════════════════════════════════
# TENANT DOMAINS
# ══════════════════════════════════════════════

@router.get("/current/domains", response_model=list[TenantDomainRead])
async def list_domains(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all custom domains for the current tenant."""
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "settings.view")

    result = await db.execute(
        text("SELECT id, tenant_id, domain, is_primary, is_verified, created_at FROM tenant_domains WHERE tenant_id = :tid ORDER BY is_primary DESC, created_at"),
        {"tid": str(tenant_id)},
    )
    rows = result.mappings().all()
    return [TenantDomainRead(**dict(r)) for r in rows]


@router.post("/current/domains", response_model=TenantDomainRead, status_code=status.HTTP_201_CREATED)
async def add_domain(
    body: TenantDomainCreate,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a custom domain to the current tenant. Requires settings.manage."""
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "settings.manage")

    # Check domain uniqueness
    existing = await db.execute(
        text("SELECT 1 FROM tenant_domains WHERE domain = :domain"),
        {"domain": body.domain},
    )
    if existing.first():
        raise HTTPException(status_code=409, detail="هذا النطاق مسجل مسبقاً")

    # If setting as primary, unset other primaries
    if body.is_primary:
        await db.execute(
            text("UPDATE tenant_domains SET is_primary = false WHERE tenant_id = :tid"),
            {"tid": str(tenant_id)},
        )

    result = await db.execute(
        text("""
            INSERT INTO tenant_domains (tenant_id, domain, is_primary)
            VALUES (:tid, :domain, :is_primary)
            RETURNING id, tenant_id, domain, is_primary, is_verified, created_at
        """),
        {"tid": str(tenant_id), "domain": body.domain, "is_primary": body.is_primary},
    )
    row = result.mappings().first()

    await log_audit(
        db, tenant_id=tenant_id, actor_user_id=user.id,
        action="domain.add", resource_type="tenant_domain",
        resource_id=str(row["id"]),
        metadata={"domain": body.domain},
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    return TenantDomainRead(**dict(row))


@router.delete("/current/domains/{domain_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_domain(
    domain_id: UUID,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a custom domain from the current tenant."""
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "settings.manage")

    result = await db.execute(
        text("DELETE FROM tenant_domains WHERE id = :did AND tenant_id = :tid RETURNING domain"),
        {"did": str(domain_id), "tid": str(tenant_id)},
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="النطاق غير موجود")

    await log_audit(
        db, tenant_id=tenant_id, actor_user_id=user.id,
        action="domain.remove", resource_type="tenant_domain",
        resource_id=str(domain_id),
        metadata={"domain": row[0]},
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()


# ══════════════════════════════════════════════
# FEATURE FLAGS
# ══════════════════════════════════════════════

@router.get("/current/features", response_model=list)
async def list_feature_flags(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all feature flags for the current tenant."""
    tenant_id = get_tenant_id_from_header(request)
    await verify_membership(db, tenant_id, user.id)

    result = await db.execute(
        text("SELECT tenant_id, flag_key, enabled, metadata, updated_at FROM feature_flags WHERE tenant_id = :tid ORDER BY flag_key"),
        {"tid": str(tenant_id)},
    )
    rows = result.mappings().all()
    return [dict(r) for r in rows]


@router.put("/current/features/{flag_key}")
async def toggle_feature_flag(
    flag_key: str,
    request: Request,
    enabled: bool = True,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Enable or disable a feature flag. Requires features.manage."""
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "features.manage")

    result = await db.execute(
        text("""
            INSERT INTO feature_flags (tenant_id, flag_key, enabled)
            VALUES (:tid, :key, :enabled)
            ON CONFLICT (tenant_id, flag_key)
            DO UPDATE SET enabled = :enabled, updated_at = now()
            RETURNING tenant_id, flag_key, enabled, metadata, updated_at
        """),
        {"tid": str(tenant_id), "key": flag_key, "enabled": enabled},
    )
    row = result.mappings().first()

    await log_audit(
        db, tenant_id=tenant_id, actor_user_id=user.id,
        action="feature.toggle", resource_type="feature_flag",
        resource_id=flag_key,
        metadata={"enabled": enabled},
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    return dict(row)
