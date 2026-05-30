"""
Tenant Context using Python contextvars.
Stores the current tenant for the duration of a request.
Any code can call get_current_tenant() without passing tenant as a parameter.
"""
import contextvars
from uuid import UUID
from typing import Optional
from pydantic import BaseModel

_current_tenant_var: contextvars.ContextVar[Optional[dict]] = contextvars.ContextVar(
    "current_tenant", default=None
)


class TenantContext(BaseModel):
    id: UUID
    slug: str
    name: str
    status: str
    plan: str


def set_current_tenant(tenant: dict) -> None:
    """Set the current tenant in the context."""
    _current_tenant_var.set(tenant)


def get_current_tenant() -> Optional[dict]:
    """Get the current tenant from the context."""
    return _current_tenant_var.get()


def get_current_tenant_id() -> Optional[UUID]:
    """Get the current tenant ID from the context."""
    tenant = _current_tenant_var.get()
    if tenant:
        return tenant.get("id")
    return None


def clear_current_tenant() -> None:
    """Clear the current tenant from the context."""
    _current_tenant_var.set(None)
