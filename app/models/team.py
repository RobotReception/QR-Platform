from pydantic import BaseModel, Field
from typing import Optional, Literal
from uuid import UUID
from datetime import datetime


class TeamCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    color: str = "#6366f1"
    leader_id: Optional[UUID] = None
    member_ids: Optional[list[UUID]] = []


class TeamRead(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    description: Optional[str] = None
    color: Optional[str] = None
    is_active: bool
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    members_count: Optional[int] = 0
    leader_name: Optional[str] = None


class TeamUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    color: Optional[str] = None
    is_active: Optional[bool] = None


class TeamMemberRead(BaseModel):
    id: UUID
    team_id: UUID
    user_id: UUID
    role: str
    joined_at: datetime
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None


class TeamMemberAdd(BaseModel):
    user_id: UUID
    role: Literal["member", "team_lead"] = "member"
