"""
Permission checking service.
Central place to verify if a user has a specific permission in a tenant.
Supports both simple role-based checks and granular RBAC permission checks.
"""
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status


async def has_permission(
    db: AsyncSession,
    tenant_id: UUID,
    user_id: UUID,
    permission_key: str,
) -> bool:
    """
    Check if a user has a specific permission in a tenant.
    Owner and Admin roles automatically have all permissions.
    """
    result = await db.execute(
        text("SELECT public.user_has_permission(:tid, :uid, :pkey)"),
        {"tid": str(tenant_id), "uid": str(user_id), "pkey": permission_key},
    )
    return result.scalar() or False


async def require_permission(
    db: AsyncSession,
    tenant_id: UUID,
    user_id: UUID,
    permission_key: str,
) -> None:
    """Raise 403 if user doesn't have the required permission."""
    allowed = await has_permission(db, tenant_id, user_id, permission_key)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"ليس لديك صلاحية: {permission_key}",
        )


async def get_user_permissions(
    db: AsyncSession,
    tenant_id: UUID,
    user_id: UUID,
) -> list[str]:
    """Get all permissions a user has in a tenant."""
    result = await db.execute(
        text("SELECT public.get_user_permissions(:tid, :uid)"),
        {"tid": str(tenant_id), "uid": str(user_id)},
    )
    return [row[0] for row in result.fetchall()]


async def get_user_tenants_with_roles(
    db: AsyncSession,
    user_id: UUID,
) -> list[dict]:
    """Get all tenants a user belongs to with their role and status."""
    result = await db.execute(
        text("""
            SELECT t.id AS tenant_id, t.slug, t.name, t.status AS tenant_status,
                   t.plan, m.role, m.status AS membership_status
            FROM memberships m
            JOIN tenants t ON t.id = m.tenant_id
            WHERE m.user_id = :uid AND m.status = 'active'
            ORDER BY t.created_at DESC
        """),
        {"uid": str(user_id)},
    )
    return [dict(r) for r in result.mappings().all()]
