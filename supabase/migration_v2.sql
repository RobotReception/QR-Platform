-- ============================================================
-- Migration V2: Complete SaaS Core
-- Adds: tenant_domains, tenant metadata/expires_at,
--       profile enhancements, default permissions seed,
--       provisioning function, permission check function
-- ============================================================

-- ============================================================
-- 1) ENHANCE TENANTS: metadata, expires_at, plan field
-- ============================================================

ALTER TABLE public.tenants ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}';
ALTER TABLE public.tenants ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;
ALTER TABLE public.tenants ADD COLUMN IF NOT EXISTS plan TEXT NOT NULL DEFAULT 'free';

-- Add 'trial' and 'cancelled' to tenant_status if not exists
-- (We recreate the enum safely)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'trial' AND enumtypid = 'tenant_status'::regtype) THEN
        ALTER TYPE tenant_status ADD VALUE 'trial';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'cancelled' AND enumtypid = 'tenant_status'::regtype) THEN
        ALTER TYPE tenant_status ADD VALUE 'cancelled';
    END IF;
END$$;

-- ============================================================
-- 2) ENHANCE PROFILES: is_staff, status, email_verified_at, last_login_at
-- ============================================================

ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS is_staff BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'active';
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMPTZ;
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ;

-- ============================================================
-- 3) TENANT DOMAINS (custom domains per tenant)
-- ============================================================

CREATE TABLE IF NOT EXISTS public.tenant_domains (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id   UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    domain      TEXT NOT NULL UNIQUE,
    is_primary  BOOLEAN NOT NULL DEFAULT false,
    is_verified BOOLEAN NOT NULL DEFAULT false,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tenant_domains_tenant_id ON public.tenant_domains(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tenant_domains_domain ON public.tenant_domains(domain);

-- RLS for tenant_domains
ALTER TABLE public.tenant_domains ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Members can view their tenant domains"
    ON public.tenant_domains FOR SELECT
    USING (tenant_id IN (SELECT public.get_my_tenant_ids()));

CREATE POLICY "Admins can manage tenant domains"
    ON public.tenant_domains FOR ALL
    USING (public.is_admin_of(tenant_id));

-- ============================================================
-- 4) ENHANCE MEMBERSHIPS: invited_by, invited_at, accepted_at
-- ============================================================

ALTER TABLE public.memberships ADD COLUMN IF NOT EXISTS invited_by UUID REFERENCES public.profiles(id);
ALTER TABLE public.memberships ADD COLUMN IF NOT EXISTS invited_at TIMESTAMPTZ;
ALTER TABLE public.memberships ADD COLUMN IF NOT EXISTS accepted_at TIMESTAMPTZ;

-- ============================================================
-- 5) SEED DEFAULT PERMISSIONS
-- ============================================================

INSERT INTO public.permissions (key, description) VALUES
    -- Users / Members
    ('users.create',    'إنشاء مستخدم جديد'),
    ('users.view',      'عرض المستخدمين'),
    ('users.edit',      'تعديل بيانات مستخدم'),
    ('users.delete',    'حذف مستخدم'),
    -- Members
    ('members.view',    'عرض أعضاء الفريق'),
    ('members.invite',  'دعوة أعضاء جدد'),
    ('members.manage',  'إدارة الأعضاء (تعديل دور، تعليق، إزالة)'),
    -- Roles
    ('roles.view',      'عرض الأدوار'),
    ('roles.manage',    'إنشاء وتعديل وحذف الأدوار'),
    -- Settings
    ('settings.view',   'عرض إعدادات المستأجر'),
    ('settings.manage', 'إدارة إعدادات المستأجر'),
    -- Billing
    ('billing.view',    'عرض الاشتراك والفواتير'),
    ('billing.manage',  'إدارة الاشتراك والدفع'),
    -- Audit
    ('audit.view',      'عرض سجل التدقيق'),
    -- Reports
    ('reports.view',    'عرض التقارير'),
    ('reports.export',  'تصدير التقارير'),
    -- Feature flags
    ('features.manage', 'إدارة الميزات')
ON CONFLICT (key) DO NOTHING;

-- ============================================================
-- 6) TENANT PROVISIONING FUNCTION
-- Auto-creates default roles + permissions when a tenant is created
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
    WHERE key IN ('users.view', 'members.view', 'settings.view', 'reports.view');

    -- Create Viewer role (read-only)
    INSERT INTO public.roles (tenant_id, name, description, is_system_role)
    VALUES (p_tenant_id, 'Viewer', 'مشاهد فقط', true)
    RETURNING id INTO v_viewer_role_id;

    INSERT INTO public.role_permissions (role_id, permission_key)
    SELECT v_viewer_role_id, key FROM public.permissions
    WHERE key IN ('users.view', 'members.view', 'reports.view');

    -- Assign Admin role to the owner
    INSERT INTO public.membership_roles (tenant_id, user_id, role_id)
    VALUES (p_tenant_id, p_owner_user_id, v_admin_role_id)
    ON CONFLICT DO NOTHING;

    -- Set default tenant settings
    INSERT INTO public.tenant_settings (tenant_id, key, value) VALUES
        (p_tenant_id, 'timezone', '"UTC"'),
        (p_tenant_id, 'language', '"ar"'),
        (p_tenant_id, 'logo_url', '""'),
        (p_tenant_id, 'primary_color', '"#6366f1"')
    ON CONFLICT DO NOTHING;
END;
$$;

-- ============================================================
-- 7) PERMISSION CHECK FUNCTION
-- Check if a user has a specific permission in a tenant
-- ============================================================

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
    SELECT EXISTS (
        SELECT 1
        FROM public.membership_roles mr
        JOIN public.role_permissions rp ON rp.role_id = mr.role_id
        WHERE mr.tenant_id = p_tenant_id
          AND mr.user_id = p_user_id
          AND rp.permission_key = p_permission_key
    )
    OR EXISTS (
        -- Owner and admin bypass (from memberships table)
        SELECT 1
        FROM public.memberships m
        WHERE m.tenant_id = p_tenant_id
          AND m.user_id = p_user_id
          AND m.status = 'active'
          AND m.role IN ('owner', 'admin')
    );
$$;

-- ============================================================
-- 8) GET USER PERMISSIONS IN TENANT
-- ============================================================

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
    -- If owner/admin, return all permissions
    SELECT DISTINCT p.key
    FROM public.permissions p
    WHERE EXISTS (
        SELECT 1 FROM public.memberships m
        WHERE m.tenant_id = p_tenant_id
          AND m.user_id = p_user_id
          AND m.status = 'active'
          AND m.role IN ('owner', 'admin')
    )
    UNION
    -- Otherwise return role-based permissions
    SELECT DISTINCT rp.permission_key
    FROM public.membership_roles mr
    JOIN public.role_permissions rp ON rp.role_id = mr.role_id
    WHERE mr.tenant_id = p_tenant_id
      AND mr.user_id = p_user_id;
$$;

-- ============================================================
-- 9) TENANT RESOLUTION BY DOMAIN
-- ============================================================

CREATE OR REPLACE FUNCTION public.resolve_tenant_by_domain(p_domain TEXT)
RETURNS UUID
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT td.tenant_id
    FROM public.tenant_domains td
    JOIN public.tenants t ON t.id = td.tenant_id
    WHERE td.domain = p_domain
      AND td.is_verified = true
      AND t.status IN ('active', 'trial')
    LIMIT 1;
$$;

CREATE OR REPLACE FUNCTION public.resolve_tenant_by_slug(p_slug TEXT)
RETURNS UUID
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT id
    FROM public.tenants
    WHERE slug = p_slug
      AND status IN ('active', 'trial')
    LIMIT 1;
$$;
