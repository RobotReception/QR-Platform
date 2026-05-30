from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.auth import get_current_user, get_tenant_id_from_header, CurrentUser
from app.database import get_db
from app.models.audit import AuditLogRead
from app.services.membership_service import require_admin

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get("", response_model=list[AuditLogRead])
async def list_audit_logs(
    request: Request,
    action: Optional[str] = Query(None, description="Filter by action"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List audit logs for the current tenant. Requires admin role."""
    tenant_id = get_tenant_id_from_header(request)
    await require_admin(db, tenant_id, user.id)

    query = """
        SELECT id, tenant_id, actor_user_id, action, resource_type, resource_id,
               metadata, ip_address::text, user_agent, created_at
        FROM audit_logs
        WHERE tenant_id = :tid
    """
    params = {"tid": str(tenant_id), "limit": limit, "offset": offset}

    if action:
        query += " AND action = :action"
        params["action"] = action

    if resource_type:
        query += " AND resource_type = :resource_type"
        params["resource_type"] = resource_type

    query += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"

    result = await db.execute(text(query), params)
    rows = result.mappings().all()
    return [AuditLogRead(**dict(r)) for r in rows]
