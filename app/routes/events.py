"""Events API: CRUD + publish + stats + gates."""
from fastapi import APIRouter, Depends, HTTPException, Request, status, Query, UploadFile, File
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
from app.models.team import EventAssignCreate, EventTeamAssignmentRead
from app.services.permission_service import require_permission, has_permission
from app.services.team_service import get_user_team_ids
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

    # ── Plan limit: events_per_month ──
    from app.services.feature_service import enforce_monthly_limit, get_plan_limit
    await enforce_monthly_limit(db, tenant_id, "events_per_month", "الأحداث الشهرية")

    # ── Plan limit: vip_quota + normal_quota ──
    inv_limit = await get_plan_limit(db, tenant_id, "invitations_per_month")
    total_requested_quota = (body.vip_quota or 0) + (body.normal_quota or 0)
    if inv_limit != -1 and total_requested_quota > inv_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"مجموع التذاكر المحددة ({total_requested_quota}) يتجاوز الحد الأقصى للدعوات الشهرية المسموح به في خطتك ({inv_limit})."
        )

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

    # ── Team visibility isolation ──
    # Org-wide managers (events.edit) see every event. Other users see only
    # unassigned events plus events assigned to teams they belong to.
    can_view_all = await has_permission(db, tenant_id, user.id, "events.edit")
    if not can_view_all:
        team_ids = await get_user_team_ids(db, tenant_id, user.id)
        if team_ids:
            placeholders = ", ".join(f":team_{i}" for i in range(len(team_ids)))
            query += f" AND (team_id IS NULL OR team_id IN ({placeholders}))"
            for i, tid in enumerate(team_ids):
                params[f"team_{i}"] = tid
        else:
            query += " AND team_id IS NULL"

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

    # ── Plan limit: vip_quota + normal_quota (update check) ──
    if body.vip_quota is not None or body.normal_quota is not None:
        existing_res = await db.execute(
            text("SELECT vip_quota, normal_quota FROM events WHERE id = :id AND tenant_id = :tid"),
            {"id": str(event_id), "tid": str(tenant_id)}
        )
        existing = existing_res.mappings().first()
        if not existing:
            raise HTTPException(404, "الحدث غير موجود")

        new_vip = body.vip_quota if body.vip_quota is not None else existing["vip_quota"]
        new_normal = body.normal_quota if body.normal_quota is not None else existing["normal_quota"]

        from app.services.feature_service import get_plan_limit
        inv_limit = await get_plan_limit(db, tenant_id, "invitations_per_month")
        total_requested_quota = (new_vip or 0) + (new_normal or 0)
        if inv_limit != -1 and total_requested_quota > inv_limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"مجموع التذاكر المحددة ({total_requested_quota}) يتجاوز الحد الأقصى للدعوات الشهرية المسموح به في خطتك ({inv_limit})."
            )

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


@router.post("/{event_id}/cover")
async def upload_event_cover(
    event_id: UUID,
    request: Request,
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a cover image for an event. Stores in Supabase Storage."""
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "events.edit")

    # Verify event exists
    event_res = await db.execute(
        text("SELECT id FROM events WHERE id = :id AND tenant_id = :tid"),
        {"id": str(event_id), "tid": str(tenant_id)},
    )
    if not event_res.mappings().first():
        raise HTTPException(404, "الحدث غير موجود")

    # Validate file type
    allowed = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
    if file.content_type not in allowed:
        raise HTTPException(400, f"نوع الملف غير مدعوم. المسموح: {', '.join(allowed)}")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(400, "حجم الملف يتجاوز 10MB")

    from app.services.feature_service import require_storage_for_upload, record_non_asset_storage
    await require_storage_for_upload(db, tenant_id, len(content))

    import uuid
    ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "png"
    safe_name = f"cover_{uuid.uuid4().hex[:8]}.{ext}"
    
    from app.services import storage_service
    path = storage_service.build_path(
        tenant_id, event_id, "cover", safe_name
    )
    storage_service.upload_file(path, content, file.content_type)
    await record_non_asset_storage(db, tenant_id, len(content))
    cover_url = storage_service.get_signed_url(path, expires_in=86400 * 365)

    # Update event cover image
    await db.execute(
        text("UPDATE events SET cover_image_url = :url, updated_at = now() WHERE id = :id AND tenant_id = :tid"),
        {"url": cover_url, "id": str(event_id), "tid": str(tenant_id)},
    )
    await db.commit()

    return {"cover_image_url": cover_url}



@router.delete("/{event_id}", status_code=204)
async def delete_event(
    event_id: UUID,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "events.delete")

    # Fetch the event first to check creation time and for audit log
    event_res = await db.execute(
        text("SELECT created_at FROM events WHERE id = :id AND tenant_id = :tid"),
        {"id": str(event_id), "tid": str(tenant_id)},
    )
    event_row = event_res.mappings().first()
    if not event_row:
        raise HTTPException(404, "الحدث غير موجود")

    created_at = event_row["created_at"]

    # Delete the event
    result = await db.execute(
        text("DELETE FROM events WHERE id = :id AND tenant_id = :tid"),
        {"id": str(event_id), "tid": str(tenant_id)},
    )
    if result.rowcount == 0:
        raise HTTPException(404, "الحدث غير موجود")

    # If created in the current month, decrement usage counter
    from datetime import datetime
    now = datetime.now(created_at.tzinfo)
    if created_at.year == now.year and created_at.month == now.month:
        await db.execute(
            text("SELECT public.increment_usage(:tenant_id, 'events_per_month', -1)"),
            {"tenant_id": str(tenant_id)},
        )

    await log_audit(db, tenant_id=tenant_id, actor_user_id=user.id,
                    action="event.delete", resource_type="event", resource_id=str(event_id),
                    ip_address=request.client.host if request.client else None)
    await db.commit()


# ══════════════════════════════════════════════
# EVENT → TEAM ASSIGNMENT (admin assigns; team lead accepts)
# ══════════════════════════════════════════════

@router.post("/{event_id}/assign", response_model=EventTeamAssignmentRead, status_code=201)
async def assign_event_to_team(
    event_id: UUID, body: EventAssignCreate, request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Assign an event to a team. The team lead must then accept/reject."""
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "teams.assign_events")

    ev = await db.execute(
        text("SELECT 1 FROM events WHERE id = :id AND tenant_id = :tid"),
        {"id": str(event_id), "tid": str(tenant_id)},
    )
    if not ev.first():
        raise HTTPException(404, "الحدث غير موجود")

    team = await db.execute(
        text("SELECT 1 FROM teams WHERE id = :id AND tenant_id = :tid"),
        {"id": str(body.team_id), "tid": str(tenant_id)},
    )
    if not team.first():
        raise HTTPException(404, "الفريق غير موجود")

    try:
        result = await db.execute(
            text("""
                INSERT INTO event_team_assignments (event_id, team_id, tenant_id, assigned_by)
                VALUES (:eid, :team, :tid, :uid)
                RETURNING *
            """),
            {"eid": str(event_id), "team": str(body.team_id),
             "tid": str(tenant_id), "uid": str(user.id)},
        )
    except Exception:
        await db.rollback()
        raise HTTPException(409, "هذا الحدث مُسند لهذا الفريق بالفعل")

    row = dict(result.mappings().first())
    await log_audit(db, tenant_id=tenant_id, actor_user_id=user.id,
                    action="event.assign_team", resource_type="event", resource_id=str(event_id),
                    ip_address=request.client.host if request.client else None)
    await db.commit()
    return EventTeamAssignmentRead(**row)


@router.get("/{event_id}/assignments", response_model=list[EventTeamAssignmentRead])
async def list_event_assignments(
    event_id: UUID, request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "events.view")

    result = await db.execute(
        text("""
            SELECT eta.*, t.name AS team_name
            FROM event_team_assignments eta
            JOIN teams t ON t.id = eta.team_id
            WHERE eta.event_id = :eid AND eta.tenant_id = :tid
            ORDER BY eta.created_at DESC
        """),
        {"eid": str(event_id), "tid": str(tenant_id)},
    )
    return [EventTeamAssignmentRead(**dict(r)) for r in result.mappings().all()]


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
            SELECT g.*, 
                   COALESCE(
                       (SELECT array_agg(user_id) FROM event_gate_users WHERE gate_id = g.id), 
                       '{}'::uuid[]
                   ) AS assigned_users
            FROM event_gates g
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

    # ── Plan limit: gates_per_event ──
    from app.services.feature_service import enforce_static_limit
    gates_count_res = await db.execute(
        text("SELECT COUNT(*) FROM event_gates WHERE event_id = :eid"),
        {"eid": str(event_id)},
    )
    current_gates = gates_count_res.scalar() or 0
    await enforce_static_limit(db, tenant_id, "gates_per_event", current_gates, "البوابات لكل حدث")

    result = await db.execute(
        text("""
            INSERT INTO event_gates (event_id, name, name_ar, allowed_classes, team_id)
            VALUES (:eid, :name, :name_ar, CAST(:classes AS ticket_class[]), :team_id)
            RETURNING id
        """),
        {
            "eid": str(event_id),
            "name": body.name,
            "name_ar": body.name_ar,
            "classes": body.allowed_classes,
            "team_id": str(body.team_id) if body.team_id else None,
        },
    )
    gate_row = result.mappings().first()
    gate_id = gate_row["id"]

    if body.assigned_users:
        for u_id in body.assigned_users:
            await db.execute(
                text("INSERT INTO event_gate_users (gate_id, user_id) VALUES (:gid, :uid) ON CONFLICT DO NOTHING"),
                {"gid": str(gate_id), "uid": str(u_id)}
            )

    gate_res = await db.execute(
        text("""
            SELECT g.*, 
                   COALESCE(
                       (SELECT array_agg(user_id) FROM event_gate_users WHERE gate_id = g.id), 
                       '{}'::uuid[]
                   ) AS assigned_users
            FROM event_gates g
            WHERE g.id = :gid
        """),
        {"gid": str(gate_id)},
    )
    row = gate_res.mappings().first()
    await db.commit()
    return EventGateRead(**dict(row))


@router.put("/{event_id}/gates/{gate_id}", response_model=EventGateRead)
async def update_gate(
    event_id: UUID,
    gate_id: UUID,
    body: EventGateCreate,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "gates.manage")

    result = await db.execute(
        text("""
            UPDATE event_gates
            SET name = :name,
                name_ar = :name_ar,
                allowed_classes = CAST(:classes AS ticket_class[]),
                team_id = :team_id
            WHERE id = :gid AND event_id = :eid
            RETURNING id
        """),
        {
            "gid": str(gate_id),
            "eid": str(event_id),
            "name": body.name,
            "name_ar": body.name_ar,
            "classes": body.allowed_classes,
            "team_id": str(body.team_id) if body.team_id else None,
        },
    )
    if result.rowcount == 0:
        raise HTTPException(404, "البوابة غير موجودة")

    await db.execute(
        text("DELETE FROM event_gate_users WHERE gate_id = :gid"),
        {"gid": str(gate_id)}
    )

    if body.assigned_users:
        for u_id in body.assigned_users:
            await db.execute(
                text("INSERT INTO event_gate_users (gate_id, user_id) VALUES (:gid, :uid)"),
                {"gid": str(gate_id), "uid": str(u_id)}
            )

    gate_res = await db.execute(
        text("""
            SELECT g.*, 
                   COALESCE(
                       (SELECT array_agg(user_id) FROM event_gate_users WHERE gate_id = g.id), 
                       '{}'::uuid[]
                   ) AS assigned_users
            FROM event_gates g
            WHERE g.id = :gid
        """),
        {"gid": str(gate_id)},
    )
    row = gate_res.mappings().first()
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
