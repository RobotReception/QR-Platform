"""
Tenant Provisioning Service.
Handles all setup when a new tenant is created:
- Default roles (Admin, Member, Designer, Check-in Staff, Viewer) with permissions
- Default settings (timezone, language, invitation defaults, etc.)
- Default feature flags for invitation platform
- Owner membership + role assignment
"""
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import logging

logger = logging.getLogger(__name__)


async def provision_tenant(
    db: AsyncSession,
    tenant_id: UUID,
    owner_user_id: UUID,
) -> None:
    """
    Full provisioning for a new tenant.
    Calls the DB function that creates roles, permissions, settings.
    """
    await db.execute(
        text("SELECT public.provision_tenant(:tid, :uid)"),
        {"tid": str(tenant_id), "uid": str(owner_user_id)},
    )
    logger.info("Provisioned tenant %s with owner %s", tenant_id, owner_user_id)


async def provision_tenant_manual(
    db: AsyncSession,
    tenant_id: UUID,
    owner_user_id: UUID,
) -> None:
    """
    Manual provisioning (fallback if DB function not available).
    Creates default roles + permissions + settings via SQL.
    """
    # Create Admin role
    admin_result = await db.execute(
        text("""
            INSERT INTO roles (tenant_id, name, description, is_system_role)
            VALUES (:tid, 'Admin', 'مدير كامل الصلاحيات', true)
            RETURNING id
        """),
        {"tid": str(tenant_id)},
    )
    admin_role_id = admin_result.scalar()

    # Assign all permissions to Admin
    await db.execute(
        text("""
            INSERT INTO role_permissions (role_id, permission_key)
            SELECT :rid, key FROM permissions
            ON CONFLICT DO NOTHING
        """),
        {"rid": str(admin_role_id)},
    )

    # Create Member role (event manager)
    member_result = await db.execute(
        text("""
            INSERT INTO roles (tenant_id, name, description, is_system_role)
            VALUES (:tid, 'Member', 'مدير أحداث ودعوات', true)
            RETURNING id
        """),
        {"tid": str(tenant_id)},
    )
    member_role_id = member_result.scalar()

    await db.execute(
        text("""
            INSERT INTO role_permissions (role_id, permission_key)
            SELECT :rid, key FROM permissions
            WHERE key IN (
                'users.view', 'members.view', 'settings.view', 'reports.view',
                'files.upload', 'files.view', 'notifications.view', 'tenant.view',
                'events.create', 'events.view', 'events.edit',
                'templates.view', 'templates.create', 'templates.edit',
                'invitations.create', 'invitations.view', 'invitations.send',
                'guests.view', 'guests.create', 'guests.edit', 'guests.import',
                'checkin.scan', 'checkin.view',
                'teams.view', 'teams.request', 'gates.view',
                'batches.create', 'batches.view'
            )
            ON CONFLICT DO NOTHING
        """),
        {"rid": str(member_role_id)},
    )
    await db.execute(
        text("""
            INSERT INTO role_permissions (role_id, permission_key)
            SELECT :rid, key FROM permissions
            WHERE key LIKE 'ui.%'
              AND key NOT IN (
                'ui.event.action.delete', 'ui.gates.action.delete',
                'ui.invitations.action.revoke', 'ui.templates.action.delete',
                'ui.members.action.create', 'ui.members.action.edit', 'ui.members.action.delete',
                'ui.roles.action.manage', 'ui.teams.action.archive'
              )
            ON CONFLICT DO NOTHING
        """),
        {"rid": str(member_role_id)},
    )

    # Create Designer role
    designer_result = await db.execute(
        text("""
            INSERT INTO roles (tenant_id, name, description, is_system_role)
            VALUES (:tid, 'Designer', 'مصمم القوالب', true)
            RETURNING id
        """),
        {"tid": str(tenant_id)},
    )
    designer_role_id = designer_result.scalar()

    await db.execute(
        text("""
            INSERT INTO role_permissions (role_id, permission_key)
            SELECT :rid, key FROM permissions
            WHERE key IN (
                'templates.view', 'templates.create', 'templates.edit',
                'files.upload', 'files.view',
                'events.view', 'invitations.view', 'tenant.view'
            )
            ON CONFLICT DO NOTHING
        """),
        {"rid": str(designer_role_id)},
    )
    await db.execute(
        text("""
            INSERT INTO role_permissions (role_id, permission_key)
            SELECT :rid, key FROM permissions
            WHERE key IN (
                'ui.nav.dashboard', 'ui.nav.events',
                'ui.event.tab.analytics', 'ui.event.tab.templates', 'ui.event.tab.settings',
                'ui.templates.action.create', 'ui.templates.action.edit', 'ui.templates.action.design'
            )
            ON CONFLICT DO NOTHING
        """),
        {"rid": str(designer_role_id)},
    )

    # Create Check-in Staff role
    checkin_result = await db.execute(
        text("""
            INSERT INTO roles (tenant_id, name, description, is_system_role)
            VALUES (:tid, 'Check-in Staff', 'موظف استقبال ومسح', true)
            RETURNING id
        """),
        {"tid": str(tenant_id)},
    )
    checkin_role_id = checkin_result.scalar()

    await db.execute(
        text("""
            INSERT INTO role_permissions (role_id, permission_key)
            SELECT :rid, key FROM permissions
            WHERE key IN (
                'checkin.scan', 'checkin.view', 'checkin.manual',
                'events.view', 'invitations.view', 'guests.view',
                'gates.view', 'tenant.view'
            )
            ON CONFLICT DO NOTHING
        """),
        {"rid": str(checkin_role_id)},
    )
    await db.execute(
        text("""
            INSERT INTO role_permissions (role_id, permission_key)
            SELECT :rid, key FROM permissions
            WHERE key IN (
                'ui.nav.dashboard', 'ui.nav.checkin', 'ui.nav.events',
                'ui.event.tab.analytics',
                'ui.checkin.action.scan', 'ui.checkin.action.manual'
            )
            ON CONFLICT DO NOTHING
        """),
        {"rid": str(checkin_role_id)},
    )

    # Create Viewer role (read-only)
    viewer_result = await db.execute(
        text("""
            INSERT INTO roles (tenant_id, name, description, is_system_role)
            VALUES (:tid, 'Viewer', 'مشاهد فقط', true)
            RETURNING id
        """),
        {"tid": str(tenant_id)},
    )
    viewer_role_id = viewer_result.scalar()

    await db.execute(
        text("""
            INSERT INTO role_permissions (role_id, permission_key)
            SELECT :rid, key FROM permissions
            WHERE key IN (
                'users.view', 'members.view', 'reports.view',
                'files.view', 'notifications.view', 'tenant.view',
                'events.view', 'invitations.view', 'guests.view',
                'checkin.view', 'templates.view', 'teams.view', 'gates.view',
                'batches.view'
            )
            ON CONFLICT DO NOTHING
        """),
        {"rid": str(viewer_role_id)},
    )
    await db.execute(
        text("""
            INSERT INTO role_permissions (role_id, permission_key)
            SELECT :rid, key FROM permissions
            WHERE key IN (
                'ui.nav.dashboard', 'ui.nav.events', 'ui.nav.invitations', 'ui.nav.checkin',
                'ui.event.tab.analytics', 'ui.event.tab.rsvp', 'ui.event.tab.final', 'ui.event.tab.barcodes'
            )
            ON CONFLICT DO NOTHING
        """),
        {"rid": str(viewer_role_id)},
    )

    # Assign Admin role to owner
    await db.execute(
        text("""
            INSERT INTO membership_roles (tenant_id, user_id, role_id)
            VALUES (:tid, :uid, :rid)
            ON CONFLICT DO NOTHING
        """),
        {"tid": str(tenant_id), "uid": str(owner_user_id), "rid": str(admin_role_id)},
    )

    # Default settings
    default_settings = [
        ("timezone", '"Asia/Riyadh"'),
        ("language", '"ar"'),
        ("date_format", '"YYYY-MM-DD"'),
        ("time_format", '"HH:mm"'),
        ("logo_url", '""'),
        ("favicon_url", '""'),
        ("primary_color", '"#6366f1"'),
        ("secondary_color", '"#8b5cf6"'),
        ("company_email", '""'),
        ("company_phone", '""'),
        ("company_address", '""'),
        ("currency", '"SAR"'),
        ("notifications_enabled", "true"),
        ("email_notifications", "true"),
        ("sms_notifications", "false"),
        ("two_factor_required", "false"),
        ("session_timeout_minutes", "60"),
        ("max_login_attempts", "5"),
        ("default_ticket_class", '"normal"'),
        ("default_invitation_expiry_days", "30"),
        ("allow_reentry_default", "false"),
        ("checkin_sound_enabled", "true"),
        ("invitation_sms_template", '""'),
        ("invitation_email_template", '""'),
    ]
    for key, value in default_settings:
        await db.execute(
            text("""
                INSERT INTO tenant_settings (tenant_id, key, value)
                VALUES (:tid, :key, CAST(:val AS jsonb))
                ON CONFLICT DO NOTHING
            """),
            {"tid": str(tenant_id), "key": key, "val": value},
        )

    # Default feature flags (invitation platform)
    default_flags = [
        ("designed_templates", False, '{"description": "قوالب بتصميم وإحداثيات"}'),
        ("rsvp", False, '{"description": "تأكيد الحضور RSVP"}'),
        ("multi_gate", False, '{"description": "بوابات متعددة"}'),
        ("sms_delivery", False, '{"description": "إرسال SMS"}'),
        ("whatsapp_delivery", False, '{"description": "إرسال WhatsApp"}'),
        ("email_delivery", True, '{"description": "إرسال بريد إلكتروني"}'),
        ("pdf_export", False, '{"description": "تصدير PDF عالي الجودة"}'),
        ("bulk_import", False, '{"description": "استيراد ضيوف جماعي"}'),
        ("advanced_reports", False, '{"description": "تقارير متقدمة"}'),
        ("api_access", False, '{"description": "الوصول لـ REST API"}'),
        ("custom_domain", False, '{"description": "نطاق مخصص"}'),
        ("white_label", False, '{"description": "إزالة العلامة التجارية"}'),
        ("audit_log", True, '{"description": "سجل التدقيق"}'),
        ("multi_language", True, '{"description": "دعم متعدد اللغات"}'),
        ("seating_management", False, '{"description": "إدارة المقاعد والطاولات"}'),
        ("vip_invitations", True, '{"description": "دعوات VIP"}'),
    ]
    for flag_key, enabled, metadata in default_flags:
        await db.execute(
            text("""
                INSERT INTO feature_flags (tenant_id, flag_key, enabled, metadata)
                VALUES (:tid, :key, :enabled, CAST(:meta AS jsonb))
                ON CONFLICT DO NOTHING
            """),
            {"tid": str(tenant_id), "key": flag_key, "enabled": enabled, "meta": metadata},
        )

    logger.info("Manually provisioned tenant %s with owner %s", tenant_id, owner_user_id)
