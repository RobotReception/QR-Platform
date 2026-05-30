"""
Dashboard Analytics — Real-time stats for tenant dashboard.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.auth import get_current_user, CurrentUser

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


async def safe_query(db: AsyncSession, sql: str, params: dict):
    """Run a query safely, returning None on error (e.g. table not found)."""
    try:
        result = await db.execute(text(sql), params)
        return result
    except Exception:
        await db.rollback()
        return None


@router.get("/analytics")
async def get_dashboard_analytics(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Comprehensive tenant dashboard analytics.
    Each section is queried separately for resilience.
    """
    tenant_id = request.headers.get("X-Tenant-ID")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="X-Tenant-ID header required")

    analytics = {}
    p = {"tid": tenant_id}

    # ── Tenant info ──
    r = await safe_query(db, """
        SELECT name, slug, status::text, plan, created_at::text, expires_at::text
        FROM tenants WHERE id = :tid
    """, p)
    if r:
        row = r.mappings().first()
        analytics["tenant"] = dict(row) if row else None
    else:
        analytics["tenant"] = None

    # ── Member stats ──
    r = await safe_query(db, """
        SELECT
            COUNT(*) FILTER (WHERE status = 'active') AS active_members,
            COUNT(*) FILTER (WHERE status = 'invited') AS pending_invites,
            COUNT(*) FILTER (WHERE status = 'disabled') AS disabled_members,
            COUNT(*) AS total_members,
            COUNT(*) FILTER (WHERE role = 'owner') AS owners,
            COUNT(*) FILTER (WHERE role = 'admin') AS admins,
            COUNT(*) FILTER (WHERE role = 'member') AS members,
            COUNT(*) FILTER (WHERE role = 'viewer') AS viewers,
            COUNT(*) FILTER (WHERE created_at >= CURRENT_DATE - INTERVAL '7 days') AS new_members_7d,
            COUNT(*) FILTER (WHERE created_at >= CURRENT_DATE - INTERVAL '30 days') AS new_members_30d
        FROM memberships WHERE tenant_id = :tid
    """, p)
    if r:
        analytics["members"] = dict(r.mappings().first())
    else:
        analytics["members"] = {"total_members": 0, "active_members": 0, "pending_invites": 0,
                                "disabled_members": 0, "owners": 0, "admins": 0, "members": 0,
                                "viewers": 0, "new_members_7d": 0, "new_members_30d": 0}

    # ── Events ──
    r = await safe_query(db, """
        SELECT
            COUNT(*) AS total_events,
            COUNT(*) FILTER (WHERE status = 'active' OR status = 'published') AS active_events,
            COUNT(*) FILTER (WHERE status = 'draft') AS draft_events,
            COUNT(*) FILTER (WHERE status = 'completed' OR status = 'ended') AS completed_events,
            COUNT(*) FILTER (WHERE status = 'cancelled') AS cancelled_events,
            COUNT(*) FILTER (WHERE created_at >= CURRENT_DATE - INTERVAL '7 days') AS new_events_7d,
            COUNT(*) FILTER (WHERE created_at >= CURRENT_DATE - INTERVAL '30 days') AS new_events_30d,
            MAX(created_at)::text AS last_event_created
        FROM events WHERE tenant_id = :tid
    """, p)
    if r:
        analytics["events"] = dict(r.mappings().first())
    else:
        analytics["events"] = {"total_events": 0, "active_events": 0, "draft_events": 0,
                               "completed_events": 0, "cancelled_events": 0, "new_events_7d": 0,
                               "new_events_30d": 0, "last_event_created": None}

    # ── Guests ──
    r = await safe_query(db, """
        SELECT
            COUNT(*) AS total_guests,
            COUNT(*) FILTER (WHERE created_at >= CURRENT_DATE - INTERVAL '7 days') AS new_guests_7d,
            COUNT(*) FILTER (WHERE created_at >= CURRENT_DATE - INTERVAL '30 days') AS new_guests_30d
        FROM guests WHERE tenant_id = :tid
    """, p)
    if r:
        guests = dict(r.mappings().first())
        guests.update({
            "confirmed_guests": 0,
            "declined_guests": 0,
            "pending_guests": guests.get("total_guests", 0),
            "checked_in_guests": 0,
        })
        analytics["guests"] = guests
    else:
        analytics["guests"] = {"total_guests": 0, "confirmed_guests": 0, "declined_guests": 0,
                               "pending_guests": 0, "checked_in_guests": 0, "new_guests_7d": 0,
                               "new_guests_30d": 0}

    # ── Digital Invitations ──
    r = await safe_query(db, """
        SELECT
            COUNT(*) AS total_invitations,
            COUNT(*) FILTER (WHERE status::text = 'sent') AS sent_invitations,
            COUNT(*) FILTER (WHERE status::text = 'delivered') AS delivered_invitations,
            COUNT(*) FILTER (WHERE status::text IN ('opened', 'viewed')) AS opened_invitations,
            COUNT(*) FILTER (WHERE status::text = 'failed') AS failed_invitations,
            COUNT(*) FILTER (WHERE created_at >= CURRENT_DATE - INTERVAL '7 days') AS new_invitations_7d
        FROM invitations WHERE tenant_id = :tid
    """, p)
    if r:
        analytics["invitations"] = dict(r.mappings().first())
    else:
        analytics["invitations"] = {"total_invitations": 0, "sent_invitations": 0,
                                    "delivered_invitations": 0, "opened_invitations": 0,
                                    "failed_invitations": 0, "new_invitations_7d": 0}

    # ── Templates ──
    r = await safe_query(db, """
        SELECT COUNT(*) AS total_templates
        FROM invite_templates WHERE tenant_id = :tid
    """, p)
    if r:
        analytics["templates"] = dict(r.mappings().first())
    else:
        analytics["templates"] = {"total_templates": 0}

    # ── Subscription ──
    r = await safe_query(db, """
        SELECT
            s.status::text AS sub_status,
            p.name AS plan_name,
            p.code AS plan_code,
            p.price_monthly,
            s.current_period_start::text,
            s.current_period_end::text,
            s.trial_ends_at::text,
            s.cancel_at_period_end
        FROM subscriptions s
        JOIN plans p ON p.id = s.plan_id
        WHERE s.tenant_id = :tid
        ORDER BY s.created_at DESC
        LIMIT 1
    """, p)
    if r:
        row = r.mappings().first()
        analytics["subscription"] = dict(row) if row else None
    else:
        analytics["subscription"] = None

    # ── Usage counters ──
    r = await safe_query(db, """
        SELECT key, value
        FROM usage_counters
        WHERE tenant_id = :tid
          AND period_start = date_trunc('month', CURRENT_DATE)::DATE
    """, p)
    if r:
        analytics["usage"] = [dict(row) for row in r.mappings().all()]
    else:
        analytics["usage"] = []

    # ── Team invites ──
    r = await safe_query(db, """
        SELECT
            COUNT(*) AS total_team_invites,
            COUNT(*) FILTER (WHERE status = 'pending') AS pending_team_invites,
            COUNT(*) FILTER (WHERE status = 'accepted') AS accepted_team_invites,
            COUNT(*) FILTER (WHERE status = 'expired') AS expired_team_invites
        FROM invites WHERE tenant_id = :tid
    """, p)
    if r:
        analytics["team_invites"] = dict(r.mappings().first())
    else:
        analytics["team_invites"] = {"total_team_invites": 0, "pending_team_invites": 0,
                                     "accepted_team_invites": 0, "expired_team_invites": 0}

    # ── Roles ──
    r = await safe_query(db, """
        SELECT
            COUNT(*) AS total_roles,
            COUNT(*) FILTER (WHERE is_system_role = true) AS system_roles,
            COUNT(*) FILTER (WHERE is_system_role = false) AS custom_roles
        FROM roles WHERE tenant_id = :tid
    """, p)
    if r:
        analytics["roles"] = dict(r.mappings().first())
    else:
        analytics["roles"] = {"total_roles": 0, "system_roles": 0, "custom_roles": 0}

    # ── Audit ──
    r = await safe_query(db, """
        SELECT
            COUNT(*) AS total_audit_entries,
            COUNT(*) FILTER (WHERE created_at >= CURRENT_DATE - INTERVAL '24 hours') AS audit_24h,
            COUNT(*) FILTER (WHERE created_at >= CURRENT_DATE - INTERVAL '7 days') AS audit_7d,
            MAX(created_at)::text AS last_activity
        FROM audit_logs WHERE tenant_id = :tid
    """, p)
    if r:
        analytics["audit"] = dict(r.mappings().first())
    else:
        analytics["audit"] = {"total_audit_entries": 0, "audit_24h": 0, "audit_7d": 0, "last_activity": None}

    # ── Recent activity ──
    r = await safe_query(db, """
        SELECT
            a.action,
            a.resource_type,
            a.resource_id,
            p.full_name AS actor_name,
            a.created_at::text,
            a.ip_address::text
        FROM audit_logs a
        LEFT JOIN profiles p ON p.id = a.actor_user_id
        WHERE a.tenant_id = :tid
        ORDER BY a.created_at DESC
        LIMIT 10
    """, p)
    if r:
        analytics["recent_activity"] = [dict(row) for row in r.mappings().all()]
    else:
        analytics["recent_activity"] = []

    # ── Settings count ──
    r = await safe_query(db, """
        SELECT COUNT(*) AS total_settings
        FROM tenant_settings WHERE tenant_id = :tid
    """, p)
    if r:
        row = r.mappings().first()
        analytics["settings_count"] = row["total_settings"] if row else 0
    else:
        analytics["settings_count"] = 0

    # ── Feature flags ──
    r = await safe_query(db, """
        SELECT
            COUNT(*) AS total_flags,
            COUNT(*) FILTER (WHERE enabled = true) AS enabled_flags,
            COUNT(*) FILTER (WHERE enabled = false) AS disabled_flags
        FROM feature_flags WHERE tenant_id = :tid
    """, p)
    if r:
        analytics["features"] = dict(r.mappings().first())
    else:
        analytics["features"] = {"total_flags": 0, "enabled_flags": 0, "disabled_flags": 0}

    # ── Top events ──
    r = await safe_query(db, """
        SELECT
            e.id::text AS event_id,
            e.title AS event_name,
            e.status::text AS status,
            COUNT(i.id) AS total_invitations,
            COUNT(i.id) FILTER (WHERE i.checked_in_at IS NOT NULL) AS checked_in,
            COUNT(i.id) FILTER (WHERE i.rsvp_status = 'confirmed') AS confirmed,
            e.start_date::text AS event_date
        FROM events e
        LEFT JOIN invitations i ON i.event_id = e.id
        WHERE e.tenant_id = :tid
        GROUP BY e.id, e.title, e.status, e.start_date, e.created_at
        ORDER BY COUNT(i.id) DESC, e.start_date DESC
        LIMIT 5
    """, p)
    if r:
        analytics["top_events"] = [dict(row) for row in r.mappings().all()]
    else:
        analytics["top_events"] = []

    # ── Members list ──
    r = await safe_query(db, """
        SELECT
            p.full_name,
            p.avatar_url,
            m.role::text,
            m.status::text,
            p.last_login_at::text AS last_login,
            m.created_at::text AS joined_at
        FROM memberships m
        JOIN profiles p ON p.id = m.user_id
        WHERE m.tenant_id = :tid
        ORDER BY m.created_at DESC
        LIMIT 20
    """, p)
    if r:
        analytics["members_list"] = [dict(row) for row in r.mappings().all()]
    else:
        analytics["members_list"] = []

    return analytics
