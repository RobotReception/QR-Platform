import sys
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
sys.path.insert(0, 'd:/QR')
import asyncio
from app.database import get_db
from sqlalchemy import text

# Mapping of legacy keys to one or more modern ui.* keys
LEGACY_TO_UI: dict[str, list[str]] = {
    "reports.view": ["ui.nav.dashboard", "ui.event.tab.analytics"],
    "members.view": ["ui.nav.users"],
    "teams.view": ["ui.nav.teams"],
    "guests.view": ["ui.nav.guests"],
    "events.view": ["ui.nav.events", "ui.event.tab.analytics"],
    "events.edit": ["ui.event.tab.settings", "ui.event.tab.registration", "ui.registration.action.manage", "ui.registration.action.approve"],
    "invitations.view": ["ui.nav.invitations", "ui.event.tab.rsvp", "ui.event.tab.final"],
    "checkin.view": ["ui.nav.checkin"],
    "settings.view": ["ui.nav.settings"],
    "gates.view": ["ui.event.tab.gates"],
    "invitations.create": ["ui.event.tab.invitations", "ui.invitations.action.generate"],
    "templates.view": ["ui.event.tab.templates"],
    "batches.view": ["ui.event.tab.barcodes"],
    "events.create": ["ui.event.action.create"],
    "events.publish": ["ui.event.action.publish"],
    "events.delete": ["ui.event.action.delete"],
    "gates.manage": ["ui.gates.action.create", "ui.gates.action.edit", "ui.gates.action.delete"],
    "invitations.send": ["ui.invitations.action.send"],
    "invitations.revoke": ["ui.invitations.action.revoke"],
    "invitations.export": ["ui.invitations.action.export", "ui.batches.action.download"],
    "reports.export": ["ui.rsvp.action.export"],
    "templates.create": ["ui.templates.action.create"],
    "templates.edit": ["ui.templates.action.edit", "ui.templates.action.design"],
    "templates.delete": ["ui.templates.action.delete"],
    "batches.manage": ["ui.batches.action.delete"],
    "guests.create": ["ui.guests.action.create"],
    "guests.edit": ["ui.guests.action.edit"],
    "guests.delete": ["ui.guests.action.delete"],
    "guests.import": ["ui.guests.action.import"],
    "teams.manage": ["ui.teams.action.create", "ui.teams.action.manage", "ui.teams.action.archive"],
    "members.manage": ["ui.members.action.create", "ui.members.action.edit", "ui.members.action.delete"],
    "checkin.scan": ["ui.checkin.action.scan"],
    "checkin.manual": ["ui.checkin.action.manual"],
    "settings.manage": ["ui.settings.action.edit"],
    "roles.manage": ["ui.roles.action.manage"],
}

async def main():
    print("Starting database permissions migration...")
    async for db in get_db():
        # 1. Update user_has_permission function DDL (owner only bypass)
        print("1. Updating public.user_has_permission function DDL...")
        await db.execute(text("""
            CREATE OR REPLACE FUNCTION public.user_has_permission(
                p_tenant_id UUID,
                p_user_id UUID,
                p_permission_key TEXT
            )
            RETURNS BOOLEAN
            LANGUAGE sql
            STABLE
            SECURITY DEFINER
            SET search_path = public
            AS $$
                -- Only owner bypasses checks
                SELECT EXISTS (
                    SELECT 1
                    FROM public.memberships m
                    WHERE m.tenant_id = p_tenant_id
                      AND m.user_id = p_user_id
                      AND m.status = 'active'
                      AND m.role = 'owner'
                )
                OR EXISTS (
                    -- Check via RBAC role_permissions
                    SELECT 1
                    FROM public.membership_roles mr
                    JOIN public.role_permissions rp ON rp.role_id = mr.role_id
                    WHERE mr.tenant_id = p_tenant_id
                      AND mr.user_id = p_user_id
                      AND rp.permission_key = p_permission_key
                );
            $$;
        """))

        # 2. Update get_user_permissions function DDL (owner only bypass)
        print("2. Updating public.get_user_permissions function DDL...")
        await db.execute(text("""
            CREATE OR REPLACE FUNCTION public.get_user_permissions(
                p_tenant_id UUID,
                p_user_id UUID
            )
            RETURNS SETOF TEXT
            LANGUAGE sql
            STABLE
            SECURITY DEFINER
            SET search_path = public
            AS $$
                -- If owner, return ALL permissions
                SELECT DISTINCT p.key
                FROM public.permissions p
                WHERE EXISTS (
                    SELECT 1 FROM public.memberships m
                    WHERE m.tenant_id = p_tenant_id
                      AND m.user_id = p_user_id
                      AND m.status = 'active'
                      AND m.role = 'owner'
                )
                UNION
                -- Otherwise return role-based permissions
                SELECT DISTINCT rp.permission_key
                FROM public.membership_roles mr
                JOIN public.role_permissions rp ON rp.role_id = mr.role_id
                WHERE mr.tenant_id = p_tenant_id
                  AND mr.user_id = p_user_id;
            $$;
        """))

        # 3. Update provision_tenant function DDL
        print("3. Updating public.provision_tenant function DDL...")
        await db.execute(text("""
            CREATE OR REPLACE FUNCTION public.provision_tenant(
                p_tenant_id UUID,
                p_owner_user_id UUID
            )
            RETURNS VOID
            LANGUAGE plpgsql
            SECURITY DEFINER
            SET search_path = public
            AS $$
            DECLARE
                v_admin_role_id UUID;
                v_member_role_id UUID;
                v_viewer_role_id UUID;
            BEGIN
                -- Create Admin role (all permissions)
                INSERT INTO public.roles (tenant_id, name, description, is_system_role)
                VALUES (p_tenant_id, 'Admin', 'مدير كامل الصلاحيات', true)
                RETURNING id INTO v_admin_role_id;

                INSERT INTO public.role_permissions (role_id, permission_key)
                SELECT v_admin_role_id, key FROM public.permissions;

                -- Create Member role (basic permissions)
                INSERT INTO public.roles (tenant_id, name, description, is_system_role)
                VALUES (p_tenant_id, 'Member', 'عضو بصلاحيات أساسية', true)
                RETURNING id INTO v_member_role_id;

                INSERT INTO public.role_permissions (role_id, permission_key)
                SELECT v_member_role_id, key FROM public.permissions
                WHERE key IN (
                    -- Sidebar Navigation
                    'ui.nav.dashboard', 'ui.nav.events', 'ui.nav.teams', 'ui.nav.settings',
                    -- Event Detail Tabs
                    'ui.event.tab.analytics', 'ui.event.tab.settings', 'ui.event.tab.gates',
                    'ui.event.tab.invitations', 'ui.event.tab.rsvp', 'ui.event.tab.registration',
                    'ui.event.tab.templates', 'ui.event.tab.barcodes', 'ui.event.tab.final',
                    -- Event Actions
                    'ui.event.action.create', 'ui.event.action.publish',
                    -- Gates
                    'ui.gates.action.create', 'ui.gates.action.edit',
                    -- Invitations
                    'ui.invitations.action.generate', 'ui.invitations.action.send',
                    'ui.invitations.action.revoke', 'ui.invitations.action.export',
                    -- RSVP
                    'ui.rsvp.action.update', 'ui.rsvp.action.export',
                    -- Registration
                    'ui.registration.action.manage', 'ui.registration.action.approve',
                    -- Templates
                    'ui.templates.action.create', 'ui.templates.action.edit', 'ui.templates.action.design',
                    -- Batches
                    'ui.batches.action.download',
                    -- Guests
                    'ui.guests.action.create', 'ui.guests.action.edit', 'ui.guests.action.import',
                    -- Teams
                    'ui.teams.action.create', 'ui.teams.action.manage',
                    -- Members
                    'ui.members.action.create', 'ui.members.action.edit',
                    -- Checkin
                    'ui.checkin.action.scan', 'ui.checkin.action.manual',
                    -- Settings
                    'ui.settings.action.edit'
                );

                -- Create Viewer role (read-only)
                INSERT INTO public.roles (tenant_id, name, description, is_system_role)
                VALUES (p_tenant_id, 'Viewer', 'مشاهد فقط', true)
                RETURNING id INTO v_viewer_role_id;

                INSERT INTO public.role_permissions (role_id, permission_key)
                SELECT v_viewer_role_id, key FROM public.permissions
                WHERE key IN (
                    -- Sidebar Navigation
                    'ui.nav.dashboard', 'ui.nav.events', 'ui.nav.settings',
                    -- Event Detail Tabs
                    'ui.event.tab.analytics', 'ui.event.tab.rsvp', 'ui.event.tab.barcodes', 'ui.event.tab.final',
                    -- Batches
                    'ui.batches.action.download',
                    -- Invitations
                    'ui.invitations.action.export',
                    -- RSVP
                    'ui.rsvp.action.export'
                );

                -- Assign Admin role to the owner
                INSERT INTO public.membership_roles (tenant_id, user_id, role_id)
                VALUES (p_tenant_id, p_owner_user_id, v_admin_role_id)
                ON CONFLICT DO NOTHING;

                -- Set default tenant settings
                INSERT INTO public.tenant_settings (tenant_id, key, value) VALUES
                    (p_tenant_id, 'timezone',       '"UTC"'),
                    (p_tenant_id, 'language',       '"ar"'),
                    (p_tenant_id, 'date_format',    '"YYYY-MM-DD"'),
                    (p_tenant_id, 'time_format',    '"HH:mm"'),
                    (p_tenant_id, 'logo_url',       '""'),
                    (p_tenant_id, 'favicon_url',    '""'),
                    (p_tenant_id, 'primary_color',  '"#6366f1"'),
                    (p_tenant_id, 'secondary_color','"#8b5cf6"'),
                    (p_tenant_id, 'company_email',  '""'),
                    (p_tenant_id, 'company_phone',  '""'),
                    (p_tenant_id, 'company_address','""'),
                    (p_tenant_id, 'currency',       '"USD"'),
                    (p_tenant_id, 'notifications_enabled', 'true'),
                    (p_tenant_id, 'email_notifications',   'true'),
                    (p_tenant_id, 'sms_notifications',     'false'),
                    (p_tenant_id, 'two_factor_required',   'false'),
                    (p_tenant_id, 'session_timeout_minutes', '60'),
                    (p_tenant_id, 'max_login_attempts',    '5')
                ON CONFLICT DO NOTHING;

                -- Set default feature flags
                INSERT INTO public.feature_flags (tenant_id, flag_key, enabled, metadata) VALUES
                    (p_tenant_id, 'advanced_reports',    false, '{"description": "تقارير متقدمة مع رسوم بيانية"}'),
                    (p_tenant_id, 'api_access',          false, '{"description": "الوصول لـ REST API"}'),
                    (p_tenant_id, 'custom_domain',       false, '{"description": "نطاق مخصص"}'),
                    (p_tenant_id, 'white_label',         false, '{"description": "إزالة العلامة التجارية"}'),
                    (p_tenant_id, 'sso_login',           false, '{"description": "تسجيل دخول موحد SSO"}'),
                    (p_tenant_id, 'audit_log',           true,  '{"description": "سجل التدقيق"}'),
                    (p_tenant_id, 'file_upload',         true,  '{"description": "رفع الملفات"}'),
                    (p_tenant_id, 'email_notifications', true,  '{"description": "إشعارات البريد"}'),
                    (p_tenant_id, 'export_data',         true,  '{"description": "تصدير البيانات"}'),
                    (p_tenant_id, 'bulk_operations',     false, '{"description": "عمليات جماعية"}'),
                    (p_tenant_id, 'webhooks',            false, '{"description": "Webhooks للتكامل"}'),
                    (p_tenant_id, 'ai_features',         false, '{"description": "ميزات الذكاء الاصطناعي"}'),
                    (p_tenant_id, 'multi_language',       true, '{"description": "دعم متعدد اللغات"}')
                ON CONFLICT DO NOTHING;
            END;
            $$;
        """))

        # 4. Translate all existing role permissions to ui.* permissions
        print("4. Migrating role permissions data...")
        roles_result = await db.execute(text("SELECT id, tenant_id, name, is_system_role FROM roles"))
        roles = roles_result.fetchall()
        for r in roles:
            role_id, tenant_id, name, is_system = r
            
            # Fetch current permissions
            perms_result = await db.execute(text("SELECT permission_key FROM role_permissions WHERE role_id = :rid"), {"rid": role_id})
            current_keys = [x[0] for x in perms_result.fetchall()]
            
            new_keys = set()
            for key in current_keys:
                if key in LEGACY_TO_UI:
                    # Translate legacy key to its ui.* equivalent(s)
                    for ui_key in LEGACY_TO_UI[key]:
                        new_keys.add(ui_key)
                else:
                    # Keep existing keys (like ui.* keys if already present, or other custom keys)
                    new_keys.add(key)
            
            # Remove any legacy keys from the new keys set
            for legacy_key in LEGACY_TO_UI.keys():
                new_keys.discard(legacy_key)
                
            # If Admin role, ensure it gets all permissions (including all ui.* keys)
            if name == "Admin" and is_system:
                all_perms_result = await db.execute(text("SELECT key FROM permissions"))
                for pk in all_perms_result.fetchall():
                    new_keys.add(pk[0])
            
            # Clear old and write new translated permissions for this role
            await db.execute(text("DELETE FROM role_permissions WHERE role_id = :rid"), {"rid": role_id})
            for pkey in new_keys:
                await db.execute(text("""
                    INSERT INTO role_permissions (role_id, permission_key)
                    VALUES (:rid, :pkey)
                    ON CONFLICT DO NOTHING
                """), {"rid": role_id, "pkey": pkey})
            
            print(f"   Migrated role '{name}' (ID={str(role_id)[:8]}) with {len(new_keys)} clean keys.")

        await db.commit()
        print("\nMigration completed successfully!")
        break

if __name__ == "__main__":
    asyncio.run(main())
