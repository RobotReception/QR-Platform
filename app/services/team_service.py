"""
Team membership helpers.

The org-level RBAC (permission_service) does not know about teams, so
team-scoped authorization (team lead / team member) lives here.
"""
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status


async def is_team_member(db: AsyncSession, team_id: UUID, user_id: UUID) -> bool:
    result = await db.execute(
        text("SELECT 1 FROM team_memberships WHERE team_id = :tid AND user_id = :uid"),
        {"tid": str(team_id), "uid": str(user_id)},
    )
    return result.first() is not None


async def is_team_lead(db: AsyncSession, team_id: UUID, user_id: UUID) -> bool:
    result = await db.execute(
        text(
            "SELECT 1 FROM team_memberships "
            "WHERE team_id = :tid AND user_id = :uid AND role = 'team_lead'"
        ),
        {"tid": str(team_id), "uid": str(user_id)},
    )
    return result.first() is not None


async def require_team_lead(db: AsyncSession, team_id: UUID, user_id: UUID) -> None:
    """Raise 403 unless the user is a lead of this team."""
    if not await is_team_lead(db, team_id, user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="هذا الإجراء مقصور على قائد الفريق",
        )


async def get_user_team_ids(db: AsyncSession, tenant_id: UUID, user_id: UUID) -> list[str]:
    """Team IDs (within the tenant) the user belongs to."""
    result = await db.execute(
        text(
            "SELECT tm.team_id FROM team_memberships tm "
            "JOIN teams t ON t.id = tm.team_id "
            "WHERE tm.user_id = :uid AND t.tenant_id = :tid"
        ),
        {"uid": str(user_id), "tid": str(tenant_id)},
    )
    return [str(r[0]) for r in result.all()]
