from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime
from enum import Enum


class EventStatus(str, Enum):
    draft = "draft"
    published = "published"
    active = "active"
    completed = "completed"
    cancelled = "cancelled"


class TicketClass(str, Enum):
    vip = "vip"
    normal = "normal"


# ── Event Categories ──

class EventCategoryRead(BaseModel):
    id: UUID
    tenant_id: Optional[UUID] = None
    name: str
    name_ar: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    sort_order: int = 0
    is_system: bool = False
    created_at: datetime


class EventCategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    name_ar: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = "#6366f1"


# ── Event Types ──

class EventTypeRead(BaseModel):
    id: UUID
    category_id: UUID
    tenant_id: Optional[UUID] = None
    name: str
    name_ar: Optional[str] = None
    description: Optional[str] = None
    is_system: bool = False
    created_at: datetime


class EventTypeCreate(BaseModel):
    category_id: UUID
    name: str = Field(..., min_length=1, max_length=100)
    name_ar: Optional[str] = None
    description: Optional[str] = None


# ── Events ──

class EventCreate(BaseModel):
    event_type_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    title: str = Field(..., min_length=1, max_length=255)
    title_ar: Optional[str] = None
    description: Optional[str] = None
    start_date: datetime
    end_date: Optional[datetime] = None
    timezone: str = "Asia/Riyadh"
    venue_name: Optional[str] = None
    venue_name_ar: Optional[str] = None
    venue_address: Optional[str] = None
    venue_city: Optional[str] = None
    venue_country: str = "SA"
    venue_map_url: Optional[str] = None
    venue_lat: Optional[float] = None
    venue_lng: Optional[float] = None
    vip_quota: int = Field(0, ge=0)
    normal_quota: int = Field(100, ge=0)
    capacity: Optional[int] = Field(None, gt=0)
    vip_capacity: Optional[int] = None
    normal_capacity: Optional[int] = None
    allow_rsvp: bool = False
    allow_plus_one: bool = False
    allow_reentry: bool = False
    require_name: bool = True
    cover_image_url: Optional[str] = None
    theme_color: str = "#6366f1"
    team_id: Optional[UUID] = None
    metadata: Optional[dict] = None


class EventRead(BaseModel):
    id: UUID
    tenant_id: UUID
    event_type_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    title: str
    title_ar: Optional[str] = None
    description: Optional[str] = None
    slug: Optional[str] = None
    start_date: datetime
    end_date: Optional[datetime] = None
    timezone: str
    venue_name: Optional[str] = None
    venue_name_ar: Optional[str] = None
    venue_address: Optional[str] = None
    venue_city: Optional[str] = None
    venue_country: Optional[str] = None
    venue_map_url: Optional[str] = None
    venue_lat: Optional[float] = None
    venue_lng: Optional[float] = None
    vip_quota: int
    normal_quota: int
    capacity: Optional[int] = None
    vip_capacity: Optional[int] = None
    normal_capacity: Optional[int] = None
    allow_rsvp: bool
    allow_plus_one: bool
    allow_reentry: bool
    require_name: bool
    cover_image_url: Optional[str] = None
    theme_color: Optional[str] = None
    status: str
    published_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[UUID] = None
    created_by: Optional[UUID] = None
    team_id: Optional[UUID] = None
    metadata: Optional[dict] = None
    created_at: datetime
    updated_at: datetime


class EventUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    title_ar: Optional[str] = None
    description: Optional[str] = None
    event_type_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    timezone: Optional[str] = None
    venue_name: Optional[str] = None
    venue_name_ar: Optional[str] = None
    venue_address: Optional[str] = None
    venue_city: Optional[str] = None
    venue_country: Optional[str] = None
    venue_map_url: Optional[str] = None
    venue_lat: Optional[float] = None
    venue_lng: Optional[float] = None
    vip_quota: Optional[int] = None
    normal_quota: Optional[int] = None
    capacity: Optional[int] = Field(None, gt=0)
    vip_capacity: Optional[int] = None
    normal_capacity: Optional[int] = None
    allow_rsvp: Optional[bool] = None
    allow_plus_one: Optional[bool] = None
    allow_reentry: Optional[bool] = None
    require_name: Optional[bool] = None
    cover_image_url: Optional[str] = None
    theme_color: Optional[str] = None
    team_id: Optional[UUID] = None
    metadata: Optional[dict] = None


# ── Event Gates ──

class EventGateRead(BaseModel):
    id: UUID
    event_id: UUID
    name: str
    name_ar: Optional[str] = None
    allowed_classes: Optional[list] = None
    is_active: bool
    created_at: datetime


class EventGateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    name_ar: Optional[str] = None
    allowed_classes: list[str] = ["normal", "vip"]


# ── Event Stats ──

class EventStats(BaseModel):
    total_invitations: int = 0
    vip_count: int = 0
    normal_count: int = 0
    sent_count: int = 0
    viewed_count: int = 0
    accepted_count: int = 0
    declined_count: int = 0
    checked_in_count: int = 0
    revoked_count: int = 0


# ── Event Assets ──

class EventAssetRead(BaseModel):
    id: UUID
    event_id: UUID
    asset_type: str
    file_url: str
    file_name: Optional[str] = None
    mime_type: Optional[str] = None
    size: int = 0
    metadata: Optional[dict] = None
    sort_order: int = 0
    created_at: datetime


class EventAssetCreate(BaseModel):
    event_id: UUID
    asset_type: str = Field(..., description="cover_image, invitation_design, logo, background, attachment")
    file_url: str
    file_name: Optional[str] = None
    mime_type: Optional[str] = None
    size: int = 0
    metadata: Optional[dict] = None
    sort_order: int = 0


# ── Event Status Transition ──

class EventStatusTransitionRequest(BaseModel):
    new_status: str = Field(..., description="draft, published, active, completed, cancelled")
