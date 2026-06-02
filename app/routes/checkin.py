"""Check-in API: scan QR, validate, manual check-in, history."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser, get_current_user, get_tenant_id_from_header
from app.database import get_db
from app.models.invitation import CheckinRead, CheckinRequest, CheckinResponse
from app.services.permission_service import require_permission

router = APIRouter(prefix="/checkin", tags=["Check-in"])


CHECKIN_MESSAGES = {
    "success": "تم تسجيل الدخول بنجاح",
    "already_checked_in": "تم تسجيل الدخول مسبقًا",
    "revoked": "الدعوة ملغاة",
    "expired": "الدعوة منتهية الصلاحية",
    "wrong_event": "الدعوة لحدث آخر",
    "wrong_gate": "البوابة غير مسموحة لهذا النوع",
    "invalid": "رمز الدعوة غير صالح",
}


@router.post("/scan", response_model=CheckinResponse)
async def scan_checkin(
    body: CheckinRequest,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Scan a QR code and process check-in."""
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "checkin.scan")

    result = await db.execute(
        text("SELECT * FROM public.validate_checkin(:token, :eid, :gid)"),
        {
            "token": body.token,
            "eid": str(body.event_id) if body.event_id else None,
            "gid": str(body.gate_id) if body.gate_id else None,
        },
    )
    row = result.mappings().first()

    if not row or not row["invitation_id"]:
        return CheckinResponse(
            result="invalid",
            message=CHECKIN_MESSAGES["invalid"],
        )

    checkin_result = row["result"]
    invitation_id = row["invitation_id"]

    inv_info_result = await db.execute(
        text("SELECT event_id, guest_count FROM invitations WHERE id = :id"),
        {"id": str(invitation_id)},
    )
    inv_info_row = inv_info_result.first()
    guest_count = inv_info_row[1] if inv_info_row else 1

    event_id_for_log = body.event_id
    if not event_id_for_log and inv_info_row:
        event_id_for_log = inv_info_row[0]

    if event_id_for_log:
        await db.execute(
            text(
                """
                INSERT INTO checkins (
                    invitation_id, event_id, gate_id, result,
                    scanned_by, scan_method, device_info, ip_address
                )
                VALUES (:iid, :eid, :gid, :result, :uid, :method, :device, :ip)
                """
            ),
            {
                "iid": str(invitation_id),
                "eid": str(event_id_for_log),
                "gid": str(body.gate_id) if body.gate_id else None,
                "result": checkin_result,
                "uid": str(user.id),
                "method": body.scan_method,
                "device": body.device_info,
                "ip": request.client.host if request.client else None,
            },
        )

    if checkin_result == "success":
        await db.execute(
            text("UPDATE invitations SET checked_in_by = :uid WHERE id = :id"),
            {"id": str(invitation_id), "uid": str(user.id)},
        )

    await db.commit()

    return CheckinResponse(
        invitation_id=invitation_id,
        result=checkin_result,
        guest_name=row.get("guest_name"),
        ticket_class=row.get("ticket_class"),
        event_title=row.get("event_title"),
        checkin_count=row.get("checkin_count", 0),
        guest_count=guest_count,
        message=CHECKIN_MESSAGES.get(checkin_result, ""),
    )


@router.post("/manual", response_model=CheckinResponse)
async def manual_checkin(
    invitation_id: UUID,
    request: Request,
    gate_id: Optional[UUID] = None,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manual check-in by invitation ID (without QR scan)."""
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "checkin.manual")

    invitation_result = await db.execute(
        text("SELECT token FROM invitations WHERE id = :id AND tenant_id = :tid"),
        {"id": str(invitation_id), "tid": str(tenant_id)},
    )
    row = invitation_result.first()
    if not row:
        raise HTTPException(404, "الدعوة غير موجودة")

    return await scan_checkin(
        CheckinRequest(token=row[0], gate_id=gate_id, scan_method="manual"),
        request,
        user,
        db,
    )


@router.get("/history", response_model=list[CheckinRead])
async def checkin_history(
    request: Request,
    event_id: Optional[UUID] = None,
    result_filter: Optional[str] = Query(None, alias="result"),
    limit: int = Query(100, le=500),
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get check-in history for an event."""
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "checkin.view")

    query = """
        SELECT c.* FROM checkins c
        JOIN events e ON e.id = c.event_id
        WHERE e.tenant_id = :tid
    """
    params: dict = {"tid": str(tenant_id)}

    if event_id:
        query += " AND c.event_id = :eid"
        params["eid"] = str(event_id)
    if result_filter:
        query += " AND c.result = :res"
        params["res"] = result_filter

    query += " ORDER BY c.created_at DESC LIMIT :lim"
    params["lim"] = limit

    result = await db.execute(text(query), params)
    return [CheckinRead(**dict(r)) for r in result.mappings().all()]


@router.get("/live/{event_id}")
async def live_stats(
    event_id: UUID,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Live check-in statistics for an event."""
    tenant_id = get_tenant_id_from_header(request)
    await require_permission(db, tenant_id, user.id, "checkin.view")

    result = await db.execute(
        text(
            """
            SELECT
                COUNT(*) FILTER (WHERE status = 'checked_in') AS checked_in,
                COUNT(*) FILTER (WHERE ticket_class = 'vip' AND status = 'checked_in') AS vip_checked_in,
                COUNT(*) FILTER (WHERE ticket_class = 'normal' AND status = 'checked_in') AS normal_checked_in,
                COUNT(*) FILTER (WHERE status NOT IN ('revoked','expired')) AS total_valid,
                COUNT(*) FILTER (WHERE ticket_class = 'vip' AND status NOT IN ('revoked','expired')) AS total_vip,
                COUNT(*) FILTER (WHERE ticket_class = 'normal' AND status NOT IN ('revoked','expired')) AS total_normal
            FROM invitations
            WHERE event_id = :eid AND tenant_id = :tid
            """
        ),
        {"eid": str(event_id), "tid": str(tenant_id)},
    )
    row = result.mappings().first()

    recent = await db.execute(
        text(
            """
            SELECT c.created_at, c.result, i.guest_name, i.ticket_class, c.scan_method
            FROM checkins c
            JOIN invitations i ON i.id = c.invitation_id
            WHERE c.event_id = :eid AND c.result = 'success'
            ORDER BY c.created_at DESC LIMIT 10
            """
        ),
        {"eid": str(event_id)},
    )

    return {
        "stats": dict(row),
        "recent_checkins": [dict(r) for r in recent.mappings().all()],
    }
