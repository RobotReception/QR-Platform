"""Guests API: CRUD + bulk import."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.auth import get_current_user, get_tenant_id_from_header, CurrentUser
from app.database import get_db
from app.models.guest import GuestCreate, GuestRead, GuestUpdate, GuestImport
from app.services.permission_service import require_permission
from app.services.audit_service import log_audit
import json

router = APIRouter(prefix="/guests", tags=["Guests"])


@router.get("", response_model=list[GuestRead])
async def list_guests(
    request: Request,
    search: str = None,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "guests.view")

    query = "SELECT * FROM guests WHERE tenant_id = :tid"
    params = {"tid": str(tenant_id)}
    if search:
        query += " AND (full_name ILIKE :s OR full_name_ar ILIKE :s OR phone ILIKE :s OR email ILIKE :s)"
        params["s"] = f"%{search}%"
    query += " ORDER BY created_at DESC LIMIT 200"

    result = await db.execute(text(query), params)
    return [GuestRead(**dict(r)) for r in result.mappings().all()]


@router.post("", response_model=GuestRead, status_code=201)
async def create_guest(
    body: GuestCreate,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "guests.create")

    result = await db.execute(
        text("""
            INSERT INTO guests (tenant_id, full_name, full_name_ar, phone, email, company, title, notes, tags, custom_fields, metadata, created_by)
            VALUES (:tid, :name, :name_ar, :phone, :email, :company, :title, :notes, :tags, :cf::jsonb, :meta::jsonb, :uid)
            RETURNING *
        """),
        {
            "tid": str(tenant_id), "name": body.full_name, "name_ar": body.full_name_ar,
            "phone": body.phone, "email": body.email, "company": body.company,
            "title": body.title, "notes": body.notes,
            "tags": body.tags, "cf": json.dumps(body.custom_fields or {}, default=str),
            "meta": json.dumps(body.metadata or {}, default=str),
            "uid": str(user.id),
        },
    )
    row = result.mappings().first()
    await db.commit()
    return GuestRead(**dict(row))


@router.get("/{guest_id}", response_model=GuestRead)
async def get_guest(
    guest_id: UUID, request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "guests.view")

    result = await db.execute(
        text("SELECT * FROM guests WHERE id = :id AND tenant_id = :tid"),
        {"id": str(guest_id), "tid": str(tenant_id)},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(404, "الضيف غير موجود")
    return GuestRead(**dict(row))


@router.patch("/{guest_id}", response_model=GuestRead)
async def update_guest(
    guest_id: UUID, body: GuestUpdate, request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "guests.edit")

    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(400, "لا توجد حقول للتعديل")

    set_clauses = ", ".join(f"{k} = :{k}" for k in updates)
    updates["id"] = str(guest_id)
    updates["tid"] = str(tenant_id)

    result = await db.execute(
        text(f"UPDATE guests SET {set_clauses}, updated_at = now() WHERE id = :id AND tenant_id = :tid RETURNING *"),
        updates,
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(404, "الضيف غير موجود")
    await db.commit()
    return GuestRead(**dict(row))


@router.delete("/{guest_id}", status_code=204)
async def delete_guest(
    guest_id: UUID, request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "guests.delete")

    result = await db.execute(
        text("DELETE FROM guests WHERE id = :id AND tenant_id = :tid"),
        {"id": str(guest_id), "tid": str(tenant_id)},
    )
    if result.rowcount == 0:
        raise HTTPException(404, "الضيف غير موجود")
    await db.commit()


@router.post("/import", status_code=201)
async def import_guests(
    body: GuestImport, request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Bulk import guests from a list."""
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "guests.import")

    imported = 0
    for g in body.guests:
        await db.execute(
            text("""
                INSERT INTO guests (tenant_id, full_name, full_name_ar, phone, email, company, title, notes, tags, custom_fields, created_by)
                VALUES (:tid, :name, :name_ar, :phone, :email, :company, :title, :notes, :tags, :cf::jsonb, :uid)
            """),
            {
                "tid": str(tenant_id), "name": g.full_name, "name_ar": g.full_name_ar,
                "phone": g.phone, "email": g.email, "company": g.company,
                "title": g.title, "notes": g.notes, "tags": g.tags,
                "cf": json.dumps(g.custom_fields or {}, default=str), "uid": str(user.id),
            },
        )
        imported += 1

    await log_audit(db, tenant_id=tenant_id, actor_user_id=user.id,
                    action="guests.import", resource_type="guest",
                    metadata={"count": imported},
                    ip_address=request.client.host if request.client else None)
    await db.commit()
    return {"imported": imported}
