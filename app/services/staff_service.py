"""Platform staff (super admin) access checks."""
from fastapi import Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, CurrentUser
from app.database import get_db


async def is_staff_user(db: AsyncSession, user_id) -> bool:
    result = await db.execute(
        text("SELECT is_staff FROM profiles WHERE id = :uid"),
        {"uid": str(user_id)},
    )
    row = result.mappings().first()
    return bool(row and row["is_staff"])


async def require_staff(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    """Ensure the user is a platform admin (is_staff=true)."""
    if not await is_staff_user(db, user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="هذا الإجراء مخصص لمشرفي المنصة فقط",
        )
    return user
