from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


class GuestCreate(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255)
    full_name_ar: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    notes: Optional[str] = None
    tags: list[str] = []
    custom_fields: Optional[dict] = None  # {"date1": "...", "seat": "A12", ...}
    metadata: Optional[dict] = None


class GuestRead(BaseModel):
    id: UUID
    tenant_id: UUID
    full_name: str
    full_name_ar: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[list[str]] = []
    custom_fields: Optional[dict] = None
    metadata: Optional[dict] = None
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime


class GuestUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    full_name_ar: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[list[str]] = None
    custom_fields: Optional[dict] = None
    metadata: Optional[dict] = None


class GuestImport(BaseModel):
    guests: list[GuestCreate]
