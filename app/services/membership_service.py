from uuid import UUID
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status


async def verify_membership(
    db: AsyncSession,
    tenant_id: UUID,
    user_id: UUID,
    required_roles: list[str] | None = None,
) -> dict:
    """
    Verify user is an active member of the tenant.
    Optionally check for specific roles.
    Returns the membership row.
    """
    result = await db.execute(
        text("""
            SELECT tenant_id, user_id, role, status
            FROM memberships
            WHERE tenant_id = :tenant_id
              AND user_id = :user_id
              AND status = 'active'
        """),
        {"tenant_id": str(tenant_id), "user_id": str(user_id)},
    )
    row = result.mappings().first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this tenant",
        )

    if required_roles and row["role"] not in required_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requires one of roles: {required_roles}. Your role: {row['role']}",
        )

    return dict(row)


async def require_admin(db: AsyncSession, tenant_id: UUID, user_id: UUID) -> dict:
    """Shortcut: verify user is owner or admin."""
    return await verify_membership(db, tenant_id, user_id, required_roles=["owner", "admin"])


async def require_owner(db: AsyncSession, tenant_id: UUID, user_id: UUID) -> dict:
    """Shortcut: verify user is owner."""
    return await verify_membership(db, tenant_id, user_id, required_roles=["owner"])
