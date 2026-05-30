-- ============================================================
-- FIX & SEED: Complete all missing items
-- Run this on existing database to bring it to schema_final.sql level
-- ============================================================

-- ============================================================
-- 1) ENABLE RLS ON MISSING TABLES
-- ============================================================

ALTER TABLE public.permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.plan_limits ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.subscription_events ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- 2) ADD MISSING TRIGGER: usage_counters
-- ============================================================

CREATE TRIGGER IF NOT EXISTS set_updated_at BEFORE UPDATE ON public.usage_counters
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

-- ============================================================
-- 3) ADD MISSING INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_profiles_is_staff ON public.profiles(is_staff) WHERE is_staff = true;
CREATE INDEX IF NOT EXISTS idx_tenants_plan ON public.tenants(plan);
CREATE INDEX IF NOT EXISTS idx_memberships_status ON public.memberships(status);
CREATE INDEX IF NOT EXISTS idx_roles_tenant_id ON public.roles(tenant_id);
CREATE INDEX IF NOT EXISTS idx_role_permissions_role_id ON public.role_permissions(role_id);
CREATE INDEX IF NOT EXISTS idx_membership_roles_role_id ON public.membership_roles(role_id);
CREATE INDEX IF NOT EXISTS idx_invites_status ON public.invites(status);
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource ON public.audit_logs(resource_type, resource_id);

-- ============================================================
-- 4) ADD MISSING COLUMN: subscriptions.canceled_at
-- ============================================================

ALTER TABLE public.subscriptions ADD COLUMN IF NOT EXISTS canceled_at TIMESTAMPTZ;

-- ============================================================
-- 5) ADD MISSING COLUMN: plans.description, plans.features
-- ============================================================

ALTER TABLE public.plans ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE public.plans ADD COLUMN IF NOT EXISTS features JSONB DEFAULT '[]';

-- ============================================================
-- 6) ADD MISSING COLUMN: tenant_domains.verified_at
-- ============================================================

ALTER TABLE public.tenant_domains ADD COLUMN IF NOT EXISTS verified_at TIMESTAMPTZ;

-- ============================================================
-- 7) ADD MISSING COLUMN: membership_roles.assigned_at
-- ============================================================

ALTER TABLE public.membership_roles ADD COLUMN IF NOT EXISTS assigned_at TIMESTAMPTZ NOT NULL DEFAULT now();

-- ============================================================
-- 8) ADD ALL MISSING RLS POLICIES
-- ============================================================

-- ── Permissions (system-wide, readable by all authenticated) ──
DO $$ BEGIN
    CREATE POLICY "Authenticated users can view permissions"
        ON public.permissions FOR SELECT
        USING (auth.uid() IS NOT NULL);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ── Roles: split "Admins can manage roles" into separate INSERT/UPDATE/DELETE ──
DO $$ BEGIN
    DROP POLICY IF EXISTS "Admins can manage roles" ON public.roles;
EXCEPTION WHEN undefined_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY "Admins can insert roles"
        ON public.roles FOR INSERT
        WITH CHECK (public.is_admin_of(tenant_id));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY "Admins can update roles"
        ON public.roles FOR UPDATE
        USING (public.is_admin_of(tenant_id));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY "Admins can delete roles"
        ON public.roles FOR DELETE
        USING (public.is_admin_of(tenant_id));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ── Role Permissions: write policies ──
DO $$ BEGIN
    CREATE POLICY "Admins can insert role permissions"
        ON public.role_permissions FOR INSERT
        WITH CHECK (
            role_id IN (
                SELECT r.id FROM public.roles r
                WHERE public.is_admin_of(r.tenant_id)
            )
        );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY "Admins can delete role permissions"
        ON public.role_permissions FOR DELETE
        USING (
            role_id IN (
                SELECT r.id FROM public.roles r
                WHERE public.is_admin_of(r.tenant_id)
            )
        );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ── Membership Roles: write policies ──
DO $$ BEGIN
    CREATE POLICY "Admins can insert membership roles"
        ON public.membership_roles FOR INSERT
        WITH CHECK (public.is_admin_of(tenant_id));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY "Admins can delete membership roles"
        ON public.membership_roles FOR DELETE
        USING (public.is_admin_of(tenant_id));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ── Plans (public read) ──
DO $$ BEGIN
    CREATE POLICY "Anyone can view active plans"
        ON public.plans FOR SELECT
        USING (auth.uid() IS NOT NULL);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ── Plan Limits (public read) ──
DO $$ BEGIN
    CREATE POLICY "Anyone can view plan limits"
        ON public.plan_limits FOR SELECT
        USING (auth.uid() IS NOT NULL);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ── Subscriptions: write policies ──
DO $$ BEGIN
    CREATE POLICY "System can insert subscriptions"
        ON public.subscriptions FOR INSERT
        WITH CHECK (public.is_admin_of(tenant_id) OR auth.uid() IS NOT NULL);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY "System can update subscriptions"
        ON public.subscriptions FOR UPDATE
        USING (public.is_admin_of(tenant_id));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ── Subscription Events ──
DO $$ BEGIN
    CREATE POLICY "Members can view subscription events"
        ON public.subscription_events FOR SELECT
        USING (
            subscription_id IN (
                SELECT s.id FROM public.subscriptions s
                WHERE s.tenant_id IN (SELECT public.get_my_tenant_ids())
            )
        );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ── Invites: rename policy + add accept policy ──
DO $$ BEGIN
    DROP POLICY IF EXISTS "Admins can view invites" ON public.invites;
EXCEPTION WHEN undefined_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY "Members can view invites in their tenants"
        ON public.invites FOR SELECT
        USING (tenant_id IN (SELECT public.get_my_tenant_ids()));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY "Invited user can accept invite"
        ON public.invites FOR UPDATE
        USING (
            email = (SELECT email FROM auth.users WHERE id = auth.uid())
            AND status = 'pending'
        );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ── Tenant Settings: split "Admins can manage" into separate policies ──
DO $$ BEGIN
    DROP POLICY IF EXISTS "Admins can manage tenant settings" ON public.tenant_settings;
EXCEPTION WHEN undefined_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY "Admins can insert tenant settings"
        ON public.tenant_settings FOR INSERT
        WITH CHECK (public.is_admin_of(tenant_id));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY "Admins can update tenant settings"
        ON public.tenant_settings FOR UPDATE
        USING (public.is_admin_of(tenant_id));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY "Admins can delete tenant settings"
        ON public.tenant_settings FOR DELETE
        USING (public.is_admin_of(tenant_id));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ── Feature Flags: full CRUD policies ──
DO $$ BEGIN
    CREATE POLICY "Admins can insert feature flags"
        ON public.feature_flags FOR INSERT
        WITH CHECK (public.is_admin_of(tenant_id));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY "Admins can update feature flags"
        ON public.feature_flags FOR UPDATE
        USING (public.is_admin_of(tenant_id));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY "Admins can delete feature flags"
        ON public.feature_flags FOR DELETE
        USING (public.is_admin_of(tenant_id));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ── Audit Logs: INSERT policy ──
DO $$ BEGIN
    CREATE POLICY "Authenticated users can insert audit logs"
        ON public.audit_logs FOR INSERT
        WITH CHECK (auth.uid() IS NOT NULL);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ============================================================
-- 9) UPDATE PLANS WITH DESCRIPTIONS AND FEATURES
-- ============================================================

UPDATE public.plans SET
    description = 'للبدء والتجربة',
    features = '["3 أعضاء", "100 رسالة/شهر", "500 MB تخزين", "50 طلب AI/شهر"]'::jsonb
WHERE code = 'free';

UPDATE public.plans SET
    description = 'للفرق المتوسطة',
    features = '["25 عضو", "5,000 رسالة/شهر", "10 GB تخزين", "2,000 طلب AI/شهر", "دعم أولوية", "تقارير متقدمة"]'::jsonb
WHERE code = 'pro';

UPDATE public.plans SET
    description = 'للمؤسسات والشركات الكبيرة',
    features = '["أعضاء غير محدود", "رسائل غير محدودة", "100 GB تخزين", "طلبات AI غير محدودة", "دعم مخصص 24/7", "SLA", "نطاق مخصص", "SSO"]'::jsonb
WHERE code = 'enterprise';

-- ============================================================
-- 10) SEED: COMPREHENSIVE DEFAULT PERMISSIONS FOR ANY SAAS
-- ============================================================

INSERT INTO public.permissions (key, description) VALUES
    -- API & Integrations
    ('api.access',          'الوصول لـ API'),
    ('api.manage',          'إدارة مفاتيح API'),
    ('integrations.view',   'عرض التكاملات'),
    ('integrations.manage', 'إدارة التكاملات'),
    -- Webhooks
    ('webhooks.view',       'عرض Webhooks'),
    ('webhooks.manage',     'إدارة Webhooks'),
    -- Files & Storage
    ('files.upload',        'رفع ملفات'),
    ('files.view',          'عرض الملفات'),
    ('files.delete',        'حذف ملفات'),
    -- Notifications
    ('notifications.view',  'عرض الإشعارات'),
    ('notifications.manage','إدارة إعدادات الإشعارات'),
    -- Domains
    ('domains.view',        'عرض النطاقات'),
    ('domains.manage',      'إدارة النطاقات المخصصة'),
    -- Tenant
    ('tenant.view',         'عرض بيانات المستأجر'),
    ('tenant.edit',         'تعديل بيانات المستأجر'),
    ('tenant.delete',       'حذف المستأجر')
ON CONFLICT (key) DO NOTHING;

-- ============================================================
-- 11) SEED: DEFAULT SYSTEM FEATURE FLAGS (for all new tenants)
-- These are the standard SaaS features that can be toggled
-- ============================================================

-- (Feature flags are per-tenant, so we just document the standard keys here)
-- The provisioning function or admin can create these per tenant.

-- ============================================================
-- 12) UPDATE PROVISIONING FUNCTION TO INCLUDE NEW PERMISSIONS
-- ============================================================

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
        'users.view', 'members.view', 'settings.view', 'reports.view',
        'files.upload', 'files.view', 'notifications.view', 'tenant.view'
    );

    -- Create Viewer role (read-only)
    INSERT INTO public.roles (tenant_id, name, description, is_system_role)
    VALUES (p_tenant_id, 'Viewer', 'مشاهد فقط', true)
    RETURNING id INTO v_viewer_role_id;

    INSERT INTO public.role_permissions (role_id, permission_key)
    SELECT v_viewer_role_id, key FROM public.permissions
    WHERE key IN (
        'users.view', 'members.view', 'reports.view',
        'files.view', 'notifications.view', 'tenant.view'
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

-- ============================================================
-- DONE
-- ============================================================
