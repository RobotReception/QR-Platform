"""Events API: CRUD + publish + stats + gates."""
from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional

from app.auth import get_current_user, get_tenant_id_from_header, CurrentUser
from app.database import get_db
from app.models.event import (
    EventCreate, EventRead, EventUpdate, EventStats,
    EventCategoryRead, EventCategoryCreate,
    EventTypeRead, EventTypeCreate,
    EventGateRead, EventGateCreate,
)
from app.services.permission_service import require_permission
from app.services.audit_service import log_audit

router = APIRouter(prefix="/events", tags=["Events"])

# ══════════════════════════════════════════════
# EVENT CATEGORIES
# ══════════════════════════════════════════════

@router.get("/categories", response_model=list[EventCategoryRead])
async def list_categories(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all event categories (system + tenant-specific)."""
    result = await db.execute(
        text("""
            SELECT id, tenant_id, name, name_ar, icon, color, sort_order, is_system, created_at
            FROM event_categories
            WHERE is_active = true AND (tenant_id IS NULL OR is_system = true)
            ORDER BY sort_order, name
        """),
    )
    return [EventCategoryRead(**dict(r)) for r in result.mappings().all()]


@router.post("/categories", response_model=EventCategoryRead, status_code=201)
async def create_category(
    body: EventCategoryCreate,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "events.create")

    result = await db.execute(
        text("""
            INSERT INTO event_categories (tenant_id, name, name_ar, icon, color)
            VALUES (:tid, :name, :name_ar, :icon, :color)
            RETURNING id, tenant_id, name, name_ar, icon, color, sort_order, is_system, created_at
        """),
        {"tid": str(tenant_id), "name": body.name, "name_ar": body.name_ar, "icon": body.icon, "color": body.color},
    )
    row = result.mappings().first()
    await db.commit()
    return EventCategoryRead(**dict(row))


# ══════════════════════════════════════════════
# EVENT TYPES
# ══════════════════════════════════════════════

@router.get("/types", response_model=list[EventTypeRead])
async def list_types(
    category_id: Optional[UUID] = None,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List event types, optionally filtered by category."""
    query = """
        SELECT id, category_id, tenant_id, name, name_ar, description, is_system, created_at
        FROM event_types WHERE is_active = true
    """
    params = {}
    if category_id:
        query += " AND category_id = :cid"
        params["cid"] = str(category_id)
    query += " ORDER BY name"

    result = await db.execute(text(query), params)
    return [EventTypeRead(**dict(r)) for r in result.mappings().all()]


# ══════════════════════════════════════════════
# EVENTS CRUD
# ══════════════════════════════════════════════

@router.post("", response_model=EventRead, status_code=201)
async def create_event(
    body: EventCreate,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "events.create")

    import re, secrets
    slug = re.sub(r'[^a-z0-9]+', '-', body.title.lower()).strip('-')
    slug = f"{slug}-{secrets.token_hex(3)}"

    # Insert the event
    result = await db.execute(
        text("""
            INSERT INTO events (
                tenant_id, title, start_date, timezone, created_by,
                vip_quota, normal_quota, allow_rsvp, allow_plus_one, allow_reentry, require_name,
                status, venue_country, theme_color, slug
            )
            VALUES (
                :tid, :title, :start, :tz, :uid,
                :vip_quota, :normal_quota, :allow_rsvp, :allow_plus_one, :allow_reentry, :require_name,
                :status, :venue_country, :theme_color, :slug
            )
        """),
        {
            "tid": str(tenant_id),
            "title": body.title,
            "start": body.start_date,
            "tz": body.timezone,
            "uid": str(user.id),
            "vip_quota": body.vip_quota,
            "normal_quota": body.normal_quota,
            "allow_rsvp": body.allow_rsvp,
            "allow_plus_one": body.allow_plus_one,
            "allow_reentry": body.allow_reentry,
            "require_name": body.require_name,
            "status": "draft",
            "venue_country": body.venue_country,
            "theme_color": body.theme_color,
            "slug": slug,
        }
    )
    await db.commit()
    
    # Get the created event
    event_result = await db.execute(
        text("SELECT * FROM events WHERE tenant_id = :tid AND slug = :slug"),
        {"tid": str(tenant_id), "slug": slug}
    )
    row = event_result.mappings().first()
    
    await log_audit(db, tenant_id=tenant_id, actor_user_id=user.id,
                    action="event.create", resource_type="event", resource_id=str(row["id"]),
                    ip_address=request.client.host if request.client else None)
    await db.commit()
    
    # Convert row to dict and return EventRead
    return EventRead(**dict(row))


@router.get("", response_model=list[EventRead])
async def list_events(
    request: Request,
    status_filter: Optional[str] = Query(None, alias="status"),
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "events.view")

    query = "SELECT * FROM events WHERE tenant_id = :tid"
    params = {"tid": str(tenant_id)}
    if status_filter:
        query += " AND status = :status"
        params["status"] = status_filter
    query += " ORDER BY start_date DESC"

    result = await db.execute(text(query), params)
    return [EventRead(**dict(r)) for r in result.mappings().all()]


@router.get("/{event_id}", response_model=EventRead)
async def get_event(
    event_id: UUID,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "events.view")

    result = await db.execute(
        text("SELECT * FROM events WHERE id = :id AND tenant_id = :tid"),
        {"id": str(event_id), "tid": str(tenant_id)},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(404, "الحدث غير موجود")
    return EventRead(**dict(row))


@router.patch("/{event_id}", response_model=EventRead)
async def update_event(
    event_id: UUID,
    body: EventUpdate,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "events.edit")

    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(400, "لا توجد حقول للتعديل")

    # Convert UUIDs to strings
    for k in ["event_type_id", "category_id", "team_id"]:
        if k in updates and updates[k] is not None:
            updates[k] = str(updates[k])

    set_clauses = ", ".join(f"{k} = :{k}" for k in updates)
    updates["id"] = str(event_id)
    updates["tid"] = str(tenant_id)

    result = await db.execute(
        text(f"UPDATE events SET {set_clauses}, updated_at = now() WHERE id = :id AND tenant_id = :tid RETURNING *"),
        updates,
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(404, "الحدث غير موجود")

    await log_audit(db, tenant_id=tenant_id, actor_user_id=user.id,
                    action="event.update", resource_type="event", resource_id=str(event_id),
                    ip_address=request.client.host if request.client else None)
    await db.commit()
    return EventRead(**dict(row))


@router.delete("/{event_id}", status_code=204)
async def delete_event(
    event_id: UUID,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "events.delete")

    result = await db.execute(
        text("DELETE FROM events WHERE id = :id AND tenant_id = :tid"),
        {"id": str(event_id), "tid": str(tenant_id)},
    )
    if result.rowcount == 0:
        raise HTTPException(404, "الحدث غير موجود")

    await log_audit(db, tenant_id=tenant_id, actor_user_id=user.id,
                    action="event.delete", resource_type="event", resource_id=str(event_id),
                    ip_address=request.client.host if request.client else None)
    await db.commit()


@router.post("/{event_id}/publish", response_model=EventRead)
async def publish_event(
    event_id: UUID,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "events.publish")

    result = await db.execute(
        text("""
            UPDATE events SET status = 'published', published_at = now(), updated_at = now()
            WHERE id = :id AND tenant_id = :tid AND status = 'draft'
            RETURNING *
        """),
        {"id": str(event_id), "tid": str(tenant_id)},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(400, "الحدث غير موجود أو تم نشره مسبقاً")

    await log_audit(db, tenant_id=tenant_id, actor_user_id=user.id,
                    action="event.publish", resource_type="event", resource_id=str(event_id),
                    ip_address=request.client.host if request.client else None)
    await db.commit()
    return EventRead(**dict(row))


# ══════════════════════════════════════════════
# EVENT STATS
# ══════════════════════════════════════════════

@router.get("/{event_id}/stats", response_model=EventStats)
async def get_event_stats(
    event_id: UUID,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "events.view")

    result = await db.execute(
        text("""
            SELECT
                COUNT(*) AS total_invitations,
                COUNT(*) FILTER (WHERE ticket_class = 'vip') AS vip_count,
                COUNT(*) FILTER (WHERE ticket_class = 'normal') AS normal_count,
                COUNT(*) FILTER (WHERE status = 'sent') AS sent_count,
                COUNT(*) FILTER (WHERE status = 'viewed') AS viewed_count,
                COUNT(*) FILTER (WHERE status = 'accepted') AS accepted_count,
                COUNT(*) FILTER (WHERE status = 'declined') AS declined_count,
                COUNT(*) FILTER (WHERE status = 'checked_in') AS checked_in_count,
                COUNT(*) FILTER (WHERE status = 'revoked') AS revoked_count
            FROM invitations
            WHERE event_id = :eid AND tenant_id = :tid
        """),
        {"eid": str(event_id), "tid": str(tenant_id)},
    )
    row = result.mappings().first()
    return EventStats(**dict(row))


# ══════════════════════════════════════════════
# EVENT GATES
# ══════════════════════════════════════════════

@router.get("/{event_id}/gates", response_model=list[EventGateRead])
async def list_gates(
    event_id: UUID,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "gates.view")

    result = await db.execute(
        text("""
            SELECT g.* FROM event_gates g
            JOIN events e ON e.id = g.event_id
            WHERE g.event_id = :eid AND e.tenant_id = :tid
            ORDER BY g.name
        """),
        {"eid": str(event_id), "tid": str(tenant_id)},
    )
    return [EventGateRead(**dict(r)) for r in result.mappings().all()]


@router.post("/{event_id}/gates", response_model=EventGateRead, status_code=201)
async def create_gate(
    event_id: UUID,
    body: EventGateCreate,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "gates.manage")

    classes_arr = "{" + ",".join(body.allowed_classes) + "}"
    result = await db.execute(
        text("""
            INSERT INTO event_gates (event_id, name, name_ar, allowed_classes)
            VALUES (:eid, :name, :name_ar, :classes::ticket_class[])
            RETURNING *
        """),
        {"eid": str(event_id), "name": body.name, "name_ar": body.name_ar, "classes": classes_arr},
    )
    row = result.mappings().first()
    await db.commit()
    return EventGateRead(**dict(row))


@router.delete("/{event_id}/gates/{gate_id}", status_code=204)
async def delete_gate(
    event_id: UUID,
    gate_id: UUID,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "gates.manage")

    result = await db.execute(
        text("DELETE FROM event_gates WHERE id = :gid AND event_id = :eid"),
        {"gid": str(gate_id), "eid": str(event_id)},
    )
    if result.rowcount == 0:
        raise HTTPException(404, "البوابة غير موجودة")
    await db.commit()
