from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime

__all__ = [
    "ProfileRead",
    "ProfileUpdate",
]


class ProfileRead(BaseModel):
    id: UUID
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    is_staff: bool = False
    status: str = "active"
    email_verified_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
