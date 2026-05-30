from pydantic import BaseModel, Field
from typing import Any, Optional
from uuid import UUID
from datetime import datetime
from enum import Enum

__all__ = [
    "TenantStatus",
    "TenantCreate",
    "TenantRead",
    "TenantUpdate",
    "TenantSettingRead",
    "TenantSettingWrite",
    "FeatureFlagRead",
]


class TenantStatus(str, Enum):
    active = "active"
    trial = "trial"
    suspended = "suspended"
    cancelled = "cancelled"
    deleted = "deleted"


class TenantCreate(BaseModel):
    slug: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")
    name: str = Field(..., min_length=1, max_length=255)
    metadata: Optional[dict] = None


class TenantRead(BaseModel):
    id: UUID
    slug: str
    name: str
    created_by: Optional[UUID] = None
    status: TenantStatus
    plan: Optional[str] = "free"
    metadata: Optional[dict] = None
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class TenantUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    slug: Optional[str] = Field(None, min_length=3, max_length=50, pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")
    metadata: Optional[dict] = None


class TenantSettingRead(BaseModel):
    tenant_id: UUID
    key: str
    value: Any
    updated_at: datetime


class TenantSettingWrite(BaseModel):
    key: str
    value: Any


class FeatureFlagRead(BaseModel):
    tenant_id: UUID
    flag_key: str
    enabled: bool
    metadata: Optional[dict] = None


class TenantDomainRead(BaseModel):
    id: UUID
    tenant_id: UUID
    domain: str
    is_primary: bool
    is_verified: bool
    created_at: datetime


class TenantDomainCreate(BaseModel):
    domain: str = Field(..., min_length=3, max_length=255)
    is_primary: bool = False
