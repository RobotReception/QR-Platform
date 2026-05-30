from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

__all__ = [
    "AuditLogCreate",
    "AuditLogRead",
]


class AuditLogCreate(BaseModel):
    tenant_id: Optional[UUID] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    metadata: Optional[dict] = None


class AuditLogRead(BaseModel):
    id: UUID
    tenant_id: Optional[UUID] = None
    actor_user_id: Optional[UUID] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    metadata: Optional[dict] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime
