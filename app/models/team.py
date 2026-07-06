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


# ── Team creation requests (approved at platform level) ──

class TeamRequestCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    color: str = "#6366f1"
    proposed_leader_id: Optional[UUID] = None


class TeamRequestReview(BaseModel):
    note: Optional[str] = None


class TeamRequestRead(BaseModel):
    id: UUID
    tenant_id: UUID
    requested_by: UUID
    name: str
    description: Optional[str] = None
    color: Optional[str] = None
    proposed_leader_id: Optional[UUID] = None
    status: str
    reviewed_by: Optional[UUID] = None
    review_note: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_team_id: Optional[UUID] = None
    created_at: datetime
    requester_name: Optional[str] = None
    tenant_name: Optional[str] = None


# ── Event → team assignments (accepted by team lead) ──

class EventAssignCreate(BaseModel):
    team_id: UUID


class AssignmentResponse(BaseModel):
    note: Optional[str] = None


class EventTeamAssignmentRead(BaseModel):
    id: UUID
    event_id: UUID
    team_id: UUID
    tenant_id: UUID
    assigned_by: UUID
    status: str
    responded_by: Optional[UUID] = None
    response_note: Optional[str] = None
    responded_at: Optional[datetime] = None
    created_at: datetime
    event_title: Optional[str] = None
    event_start_date: Optional[datetime] = None
    team_name: Optional[str] = None
