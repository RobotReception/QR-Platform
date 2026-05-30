from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, CurrentUser
from app.database import get_db
from app.models.profile import ProfileRead, ProfileUpdate

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get("/me", response_model=ProfileRead)
async def get_my_profile(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's profile."""
    result = await db.execute(
        text("""
            SELECT id, full_name, avatar_url, phone, is_staff, status,
                   email_verified_at, last_login_at, created_at, updated_at
            FROM profiles WHERE id = :id
        """),
        {"id": str(user.id)},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")
    return ProfileRead(**dict(row))


@router.patch("/me", response_model=ProfileRead)
async def update_my_profile(
    body: ProfileUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the current user's profile."""
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clauses = ", ".join(f"{k} = :{k}" for k in updates)
    updates["id"] = str(user.id)

    result = await db.execute(
        text(f"""
            UPDATE profiles SET {set_clauses}, updated_at = now()
            WHERE id = :id
            RETURNING id, full_name, avatar_url, phone, is_staff, status,
                      email_verified_at, last_login_at, created_at, updated_at
        """),
        updates,
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")

    await db.commit()
    return ProfileRead(**dict(row))
