-- Auto-generated bootstrap schema for the full invitations platform.
-- Applies core SaaS schema plus invitations/platform migrations in order.


-- >>> BEGIN schema_final.sql >>>

-- ============================================================
-- SaaS Core Schema v2.0 (Final Consolidated)
-- ============================================================
-- Run this ONCE on a fresh Supabase project.
-- It includes everything: tables, enums, indexes, triggers,
-- RLS policies, helper functions, seed data, provisioning.
-- ============================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- ENUMS
-- ============================================================

CREATE TYPE tenant_status AS ENUM ('active', 'trial', 'suspended', 'cancelled', 'deleted');
CREATE TYPE membership_status AS ENUM ('active', 'invited', 'disabled');
CREATE TYPE membership_role AS ENUM ('owner', 'admin', 'member', 'viewer');
CREATE TYPE subscription_status AS ENUM ('trialing', 'active', 'past_due', 'canceled', 'unpaid', 'incomplete');
CREATE TYPE invite_status AS ENUM ('pending', 'accepted', 'expired', 'revoked');
CREATE TYPE usage_period AS ENUM ('month', 'day', 'none');

-- ============================================================
-- 1) PROFILES
-- ============================================================

CREATE TABLE public.profiles (
    id                  UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name           TEXT,
    avatar_url          TEXT,
    phone               TEXT,
    is_staff            BOOLEAN NOT NULL DEFAULT false,
    status              TEXT NOT NULL DEFAULT 'active',
    email_verified_at   TIMESTAMPTZ,
    last_login_at       TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_profiles_created_at ON public.profiles(created_at);
CREATE INDEX idx_profiles_is_staff ON public.profiles(is_staff) WHERE is_staff = true;

-- Auto-create profile on signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public
AS $$
BEGIN
    INSERT INTO public.profiles (id, full_name, avatar_url)
    VALUES (
        NEW.id,
        COALESCE(NEW.raw_user_meta_data ->> 'full_name', ''),
        COALESCE(NEW.raw_user_meta_data ->> 'avatar_url', '')
    );
    RETURN NEW;
END;
$$;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ============================================================
-- 2) TENANTS
-- ============================================================

CREATE TABLE public.tenants (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slug        TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL,
    created_by  UUID REFERENCES public.profiles(id),
    status      tenant_status NOT NULL DEFAULT 'active',
    plan        TEXT NOT NULL DEFAULT 'free',
    metadata    JSONB DEFAULT '{}',
    expires_at  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_tenants_slug ON public.tenants(slug);
CREATE INDEX idx_tenants_status ON public.tenants(status);
CREATE INDEX idx_tenants_created_by ON public.tenants(created_by);
CREATE INDEX idx_tenants_plan ON public.tenants(plan);

-- ============================================================
-- 3) TENANT DOMAINS (custom domains per tenant)
-- ============================================================

CREATE TABLE public.tenant_domains (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id   UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    domain      TEXT NOT NULL UNIQUE,
    is_primary  BOOLEAN NOT NULL DEFAULT false,
    is_verified BOOLEAN NOT NULL DEFAULT false,
    verified_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_tenant_domains_tenant_id ON public.tenant_domains(tenant_id);
CREATE INDEX idx_tenant_domains_domain ON public.tenant_domains(domain);

-- ============================================================
-- 4) MEMBERSHIPS (users <-> tenants)
-- ============================================================

CREATE TABLE public.memberships (
    tenant_id   UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    role        membership_role NOT NULL DEFAULT 'member',
    status      membership_status NOT NULL DEFAULT 'active',
    invited_by  UUID REFERENCES public.profiles(id),
    invited_at  TIMESTAMPTZ,
    accepted_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, user_id)
);

CREATE INDEX idx_memberships_user_id ON public.memberships(user_id);
CREATE INDEX idx_memberships_tenant_id ON public.memberships(tenant_id);
CREATE INDEX idx_memberships_role ON public.memberships(role);
CREATE INDEX idx_memberships_status ON public.memberships(status);

-- ============================================================
-- 5) ROLES (per tenant, system + custom)
-- ============================================================

CREATE TABLE public.roles (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    description     TEXT,
    is_system_role  BOOLEAN NOT NULL DEFAULT false,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(tenant_id, name)
);

CREATE INDEX idx_roles_tenant_id ON public.roles(tenant_id);

-- ============================================================
-- 6) PERMISSIONS (system-wide)
-- ============================================================

CREATE TABLE public.permissions (
    key         TEXT PRIMARY KEY,
    description TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- 7) ROLE_PERMISSIONS (which permissions each role has)
-- ============================================================

CREATE TABLE public.role_permissions (
    role_id         UUID NOT NULL REFERENCES public.roles(id) ON DELETE CASCADE,
    permission_key  TEXT NOT NULL REFERENCES public.permissions(key) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_key)
);

CREATE INDEX idx_role_permissions_role_id ON public.role_permissions(role_id);

-- ============================================================
-- 8) MEMBERSHIP_ROLES (which roles each member has)
-- ============================================================

CREATE TABLE public.membership_roles (
    tenant_id   UUID NOT NULL,
    user_id     UUID NOT NULL,
    role_id     UUID NOT NULL REFERENCES public.roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, user_id, role_id),
    FOREIGN KEY (tenant_id, user_id) REFERENCES public.memberships(tenant_id, user_id) ON DELETE CASCADE
);

CREATE INDEX idx_membership_roles_role_id ON public.membership_roles(role_id);

-- ============================================================
-- 9) PLANS (system-wide)
-- ============================================================

CREATE TABLE public.plans (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code            TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    description     TEXT,
    price_monthly   NUMERIC(10, 2) NOT NULL DEFAULT 0,
    price_yearly    NUMERIC(10, 2),
    currency        TEXT NOT NULL DEFAULT 'USD',
    is_active       BOOLEAN NOT NULL DEFAULT true,
    features        JSONB DEFAULT '[]',
    sort_order      INT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_plans_code ON public.plans(code);

-- ============================================================
-- 10) PLAN LIMITS (entitlements per plan)
-- ============================================================

CREATE TABLE public.plan_limits (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    plan_id     UUID NOT NULL REFERENCES public.plans(id) ON DELETE CASCADE,
    key         TEXT NOT NULL,
    value       BIGINT NOT NULL,
    period      usage_period NOT NULL DEFAULT 'none',
    UNIQUE(plan_id, key)
);

CREATE INDEX idx_plan_limits_plan_id ON public.plan_limits(plan_id);

-- ============================================================
-- 11) SUBSCRIPTIONS (per tenant)
-- ============================================================

CREATE TABLE public.subscriptions (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id                   UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    plan_id                     UUID NOT NULL REFERENCES public.plans(id),
    provider                    TEXT NOT NULL DEFAULT 'stripe',
    provider_customer_id        TEXT,
    provider_subscription_id    TEXT,
    status                      subscription_status NOT NULL DEFAULT 'trialing',
    current_period_start        TIMESTAMPTZ,
    current_period_end          TIMESTAMPTZ,
    cancel_at_period_end        BOOLEAN NOT NULL DEFAULT false,
    trial_ends_at               TIMESTAMPTZ,
    canceled_at                 TIMESTAMPTZ,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_subscriptions_tenant_id ON public.subscriptions(tenant_id);
CREATE INDEX idx_subscriptions_status ON public.subscriptions(status);
CREATE INDEX idx_subscriptions_provider_sub_id ON public.subscriptions(provider_subscription_id);

-- ============================================================
-- 12) SUBSCRIPTION EVENTS (billing audit trail)
-- ============================================================

CREATE TABLE public.subscription_events (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    subscription_id     UUID NOT NULL REFERENCES public.subscriptions(id) ON DELETE CASCADE,
    event_type          TEXT NOT NULL,
    provider_event_id   TEXT,
    raw_payload         JSONB,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_sub_events_subscription_id ON public.subscription_events(subscription_id);
CREATE INDEX idx_sub_events_event_type ON public.subscription_events(event_type);

-- ============================================================
-- 13) USAGE COUNTERS
-- ============================================================

CREATE TABLE public.usage_counters (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    period_start    DATE NOT NULL,
    period_end      DATE NOT NULL,
    key             TEXT NOT NULL,
    value           BIGINT NOT NULL DEFAULT 0,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(tenant_id, period_start, key)
);

CREATE INDEX idx_usage_counters_tenant_period ON public.usage_counters(tenant_id, period_start);

-- ============================================================
-- 14) INVITES
-- ============================================================

CREATE TABLE public.invites (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id   UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    email       TEXT NOT NULL,
    role        membership_role NOT NULL DEFAULT 'member',
    token       TEXT NOT NULL UNIQUE DEFAULT encode(gen_random_bytes(32), 'hex'),
    status      invite_status NOT NULL DEFAULT 'pending',
    invited_by  UUID NOT NULL REFERENCES public.profiles(id),
    expires_at  TIMESTAMPTZ NOT NULL DEFAULT (now() + INTERVAL '7 days'),
    accepted_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_invites_tenant_id ON public.invites(tenant_id);
CREATE INDEX idx_invites_email ON public.invites(email);
CREATE INDEX idx_invites_token ON public.invites(token);
CREATE INDEX idx_invites_status ON public.invites(status);

-- ============================================================
-- 15) TENANT SETTINGS
-- ============================================================

CREATE TABLE public.tenant_settings (
    tenant_id   UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    key         TEXT NOT NULL,
    value       JSONB NOT NULL DEFAULT '{}',
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, key)
);

-- ============================================================
-- 16) FEATURE FLAGS
-- ============================================================

CREATE TABLE public.feature_flags (
    tenant_id   UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    flag_key    TEXT NOT NULL,
    enabled     BOOLEAN NOT NULL DEFAULT false,
    metadata    JSONB,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, flag_key)
);

-- ============================================================
-- 17) AUDIT LOGS
-- ============================================================

CREATE TABLE public.audit_logs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID REFERENCES public.tenants(id) ON DELETE SET NULL,
    actor_user_id   UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    action          TEXT NOT NULL,
    resource_type   TEXT,
    resource_id     TEXT,
    metadata        JSONB DEFAULT '{}',
    ip_address      INET,
    user_agent      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_audit_logs_tenant_id ON public.audit_logs(tenant_id);
CREATE INDEX idx_audit_logs_actor ON public.audit_logs(actor_user_id);
CREATE INDEX idx_audit_logs_action ON public.audit_logs(action);
CREATE INDEX idx_audit_logs_created_at ON public.audit_logs(created_at DESC);
CREATE INDEX idx_audit_logs_resource ON public.audit_logs(resource_type, resource_id);

-- ============================================================
-- 18) UPDATED_AT TRIGGER (reusable)
-- ============================================================

CREATE OR REPLACE FUNCTION public.update_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.profiles
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.tenants
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.memberships
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.plans
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.subscriptions
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.usage_counters
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.tenant_settings
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.feature_flags
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

-- ============================================================
-- 19) ATOMIC USAGE INCREMENT FUNCTION
-- ============================================================

CREATE OR REPLACE FUNCTION public.increment_usage(
    p_tenant_id UUID,
    p_key TEXT,
    p_amount BIGINT DEFAULT 1
)
RETURNS BIGINT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_period_start DATE;
    v_period_end DATE;
    v_new_value BIGINT;
BEGIN
    v_period_start := date_trunc('month', CURRENT_DATE)::DATE;
    v_period_end := (date_trunc('month', CURRENT_DATE) + INTERVAL '1 month' - INTERVAL '1 day')::DATE;

    INSERT INTO public.usage_counters (tenant_id, period_start, period_end, key, value)
    VALUES (p_tenant_id, v_period_start, v_period_end, p_key, p_amount)
    ON CONFLICT (tenant_id, period_start, key)
    DO UPDATE SET
        value = usage_counters.value + p_amount,
        updated_at = now()
    RETURNING value INTO v_new_value;

    RETURN v_new_value;
END;
$$;

-- ============================================================
-- 20) RLS HELPER FUNCTIONS
-- ============================================================

-- Get tenant IDs for current user
CREATE OR REPLACE FUNCTION public.get_my_tenant_ids()
RETURNS SETOF UUID
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT tenant_id
    FROM public.memberships
    WHERE user_id = auth.uid()
      AND status = 'active';
$$;

-- Check if user is member of tenant
CREATE OR REPLACE FUNCTION public.is_member_of(p_tenant_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.memberships
        WHERE tenant_id = p_tenant_id
          AND user_id = auth.uid()
          AND status = 'active'
    );
$$;

-- Check if user has specific role in tenant
CREATE OR REPLACE FUNCTION public.has_role_in(p_tenant_id UUID, p_role membership_role)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.memberships
        WHERE tenant_id = p_tenant_id
          AND user_id = auth.uid()
          AND status = 'active'
          AND role = p_role
    );
$$;

-- Check if user is owner or admin
CREATE OR REPLACE FUNCTION public.is_admin_of(p_tenant_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.memberships
        WHERE tenant_id = p_tenant_id
          AND user_id = auth.uid()
          AND status = 'active'
          AND role IN ('owner', 'admin')
    );
$$;

-- ============================================================
-- 21) PERMISSION CHECK FUNCTIONS (for API use)
-- ============================================================

-- Check if a user has a specific permission in a tenant
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
    -- Owner/admin bypass: always have all permissions
    SELECT EXISTS (
        SELECT 1
        FROM public.memberships m
        WHERE m.tenant_id = p_tenant_id
          AND m.user_id = p_user_id
          AND m.status = 'active'
          AND m.role IN ('owner', 'admin')
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

-- Get all permissions a user has in a tenant
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
    -- If owner/admin, return ALL permissions
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
-- 22) TENANT RESOLUTION FUNCTIONS
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

-- ============================================================
-- 23) TENANT PROVISIONING FUNCTION
-- Auto-creates default roles + permissions + settings
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
-- 24) ROW LEVEL SECURITY (RLS)
-- ============================================================

-- Enable RLS on ALL tables
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tenant_domains ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.role_permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.membership_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.plan_limits ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.subscription_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.usage_counters ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.invites ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tenant_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.feature_flags ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;

-- ── Profiles ──
CREATE POLICY "Users can view own profile"
    ON public.profiles FOR SELECT
    USING (id = auth.uid());

CREATE POLICY "Users can update own profile"
    ON public.profiles FOR UPDATE
    USING (id = auth.uid());

CREATE POLICY "Members can view co-member profiles"
    ON public.profiles FOR SELECT
    USING (
        id IN (
            SELECT m.user_id FROM public.memberships m
            WHERE m.tenant_id IN (SELECT public.get_my_tenant_ids())
              AND m.status = 'active'
        )
    );

-- ── Tenants ──
CREATE POLICY "Members can view their tenants"
    ON public.tenants FOR SELECT
    USING (id IN (SELECT public.get_my_tenant_ids()));

CREATE POLICY "Authenticated users can create tenants"
    ON public.tenants FOR INSERT
    WITH CHECK (auth.uid() IS NOT NULL);

CREATE POLICY "Admins can update their tenants"
    ON public.tenants FOR UPDATE
    USING (public.is_admin_of(id));

-- ── Tenant Domains ──
CREATE POLICY "Members can view their tenant domains"
    ON public.tenant_domains FOR SELECT
    USING (tenant_id IN (SELECT public.get_my_tenant_ids()));

CREATE POLICY "Admins can manage tenant domains"
    ON public.tenant_domains FOR ALL
    USING (public.is_admin_of(tenant_id));

-- ── Memberships ──
CREATE POLICY "Members can view memberships in their tenants"
    ON public.memberships FOR SELECT
    USING (tenant_id IN (SELECT public.get_my_tenant_ids()));

CREATE POLICY "Admins can insert memberships"
    ON public.memberships FOR INSERT
    WITH CHECK (public.is_admin_of(tenant_id));

CREATE POLICY "Admins can update memberships"
    ON public.memberships FOR UPDATE
    USING (public.is_admin_of(tenant_id));

CREATE POLICY "Admins can delete memberships"
    ON public.memberships FOR DELETE
    USING (public.is_admin_of(tenant_id));

-- ── Roles ──
CREATE POLICY "Members can view roles in their tenants"
    ON public.roles FOR SELECT
    USING (tenant_id IN (SELECT public.get_my_tenant_ids()));

CREATE POLICY "Admins can insert roles"
    ON public.roles FOR INSERT
    WITH CHECK (public.is_admin_of(tenant_id));

CREATE POLICY "Admins can update roles"
    ON public.roles FOR UPDATE
    USING (public.is_admin_of(tenant_id));

CREATE POLICY "Admins can delete roles"
    ON public.roles FOR DELETE
    USING (public.is_admin_of(tenant_id));

-- ── Permissions (system-wide, readable by all authenticated) ──
CREATE POLICY "Authenticated users can view permissions"
    ON public.permissions FOR SELECT
    USING (auth.uid() IS NOT NULL);

-- ── Role Permissions ──
CREATE POLICY "Members can view role permissions"
    ON public.role_permissions FOR SELECT
    USING (
        role_id IN (
            SELECT r.id FROM public.roles r
            WHERE r.tenant_id IN (SELECT public.get_my_tenant_ids())
        )
    );

CREATE POLICY "Admins can insert role permissions"
    ON public.role_permissions FOR INSERT
    WITH CHECK (
        role_id IN (
            SELECT r.id FROM public.roles r
            WHERE public.is_admin_of(r.tenant_id)
        )
    );

CREATE POLICY "Admins can delete role permissions"
    ON public.role_permissions FOR DELETE
    USING (
        role_id IN (
            SELECT r.id FROM public.roles r
            WHERE public.is_admin_of(r.tenant_id)
        )
    );

-- ── Membership Roles ──
CREATE POLICY "Members can view membership roles"
    ON public.membership_roles FOR SELECT
    USING (tenant_id IN (SELECT public.get_my_tenant_ids()));

CREATE POLICY "Admins can insert membership roles"
    ON public.membership_roles FOR INSERT
    WITH CHECK (public.is_admin_of(tenant_id));

CREATE POLICY "Admins can delete membership roles"
    ON public.membership_roles FOR DELETE
    USING (public.is_admin_of(tenant_id));

-- ── Plans (public read for all authenticated users) ──
CREATE POLICY "Anyone can view active plans"
    ON public.plans FOR SELECT
    USING (auth.uid() IS NOT NULL);

-- ── Plan Limits (public read) ──
CREATE POLICY "Anyone can view plan limits"
    ON public.plan_limits FOR SELECT
    USING (auth.uid() IS NOT NULL);

-- ── Subscriptions ──
CREATE POLICY "Members can view their tenant subscriptions"
    ON public.subscriptions FOR SELECT
    USING (tenant_id IN (SELECT public.get_my_tenant_ids()));

CREATE POLICY "System can insert subscriptions"
    ON public.subscriptions FOR INSERT
    WITH CHECK (public.is_admin_of(tenant_id) OR auth.uid() IS NOT NULL);

CREATE POLICY "System can update subscriptions"
    ON public.subscriptions FOR UPDATE
    USING (public.is_admin_of(tenant_id));

-- ── Subscription Events ──
CREATE POLICY "Members can view subscription events"
    ON public.subscription_events FOR SELECT
    USING (
        subscription_id IN (
            SELECT s.id FROM public.subscriptions s
            WHERE s.tenant_id IN (SELECT public.get_my_tenant_ids())
        )
    );

-- ── Usage Counters ──
CREATE POLICY "Members can view their tenant usage"
    ON public.usage_counters FOR SELECT
    USING (tenant_id IN (SELECT public.get_my_tenant_ids()));

-- ── Invites ──
CREATE POLICY "Members can view invites in their tenants"
    ON public.invites FOR SELECT
    USING (tenant_id IN (SELECT public.get_my_tenant_ids()));

CREATE POLICY "Admins can create invites"
    ON public.invites FOR INSERT
    WITH CHECK (public.is_admin_of(tenant_id));

CREATE POLICY "Admins can update invites"
    ON public.invites FOR UPDATE
    USING (public.is_admin_of(tenant_id));

-- Allow invited user to update invite status (accept)
CREATE POLICY "Invited user can accept invite"
    ON public.invites FOR UPDATE
    USING (
        email = (SELECT email FROM auth.users WHERE id = auth.uid())
        AND status = 'pending'
    );

-- ── Tenant Settings ──
CREATE POLICY "Members can view tenant settings"
    ON public.tenant_settings FOR SELECT
    USING (tenant_id IN (SELECT public.get_my_tenant_ids()));

CREATE POLICY "Admins can insert tenant settings"
    ON public.tenant_settings FOR INSERT
    WITH CHECK (public.is_admin_of(tenant_id));

CREATE POLICY "Admins can update tenant settings"
    ON public.tenant_settings FOR UPDATE
    USING (public.is_admin_of(tenant_id));

CREATE POLICY "Admins can delete tenant settings"
    ON public.tenant_settings FOR DELETE
    USING (public.is_admin_of(tenant_id));

-- ── Feature Flags ──
CREATE POLICY "Members can view feature flags"
    ON public.feature_flags FOR SELECT
    USING (tenant_id IN (SELECT public.get_my_tenant_ids()));

CREATE POLICY "Admins can insert feature flags"
    ON public.feature_flags FOR INSERT
    WITH CHECK (public.is_admin_of(tenant_id));

CREATE POLICY "Admins can update feature flags"
    ON public.feature_flags FOR UPDATE
    USING (public.is_admin_of(tenant_id));

CREATE POLICY "Admins can delete feature flags"
    ON public.feature_flags FOR DELETE
    USING (public.is_admin_of(tenant_id));

-- ── Audit Logs ──
CREATE POLICY "Admins can view audit logs"
    ON public.audit_logs FOR SELECT
    USING (public.is_admin_of(tenant_id));

-- Allow system to insert audit logs (any authenticated user)
CREATE POLICY "Authenticated users can insert audit logs"
    ON public.audit_logs FOR INSERT
    WITH CHECK (auth.uid() IS NOT NULL);

-- ============================================================
-- 25) SEED DATA: Default Permissions
-- ============================================================

INSERT INTO public.permissions (key, description) VALUES
    -- Users / Members
    ('users.create',        'إنشاء مستخدم جديد'),
    ('users.view',          'عرض المستخدمين'),
    ('users.edit',          'تعديل بيانات مستخدم'),
    ('users.delete',        'حذف مستخدم'),
    ('members.view',        'عرض أعضاء الفريق'),
    ('members.invite',      'دعوة أعضاء جدد'),
    ('members.manage',      'إدارة الأعضاء (تعديل دور، تعليق، إزالة)'),
    -- Roles
    ('roles.view',          'عرض الأدوار'),
    ('roles.manage',        'إنشاء وتعديل وحذف الأدوار'),
    -- Settings
    ('settings.view',       'عرض إعدادات المستأجر'),
    ('settings.manage',     'إدارة إعدادات المستأجر'),
    -- Billing
    ('billing.view',        'عرض الاشتراك والفواتير'),
    ('billing.manage',      'إدارة الاشتراك والدفع'),
    -- Audit
    ('audit.view',          'عرض سجل التدقيق'),
    -- Reports
    ('reports.view',        'عرض التقارير'),
    ('reports.export',      'تصدير التقارير'),
    -- Features
    ('features.manage',     'إدارة الميزات'),
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
-- 26) SEED DATA: Default Plans
-- ============================================================

INSERT INTO public.plans (code, name, description, price_monthly, price_yearly, currency, sort_order, features) VALUES
    ('free',       'Free',       'للبدء والتجربة',                0,       0,       'USD', 1, '["3 أعضاء", "100 رسالة/شهر", "500 MB تخزين", "50 طلب AI/شهر"]'),
    ('pro',        'Pro',        'للفرق المتوسطة',               29.00,   290.00,  'USD', 2, '["25 عضو", "5,000 رسالة/شهر", "10 GB تخزين", "2,000 طلب AI/شهر", "دعم أولوية", "تقارير متقدمة"]'),
    ('enterprise', 'Enterprise', 'للمؤسسات والشركات الكبيرة',    99.00,   990.00,  'USD', 3, '["أعضاء غير محدود", "رسائل غير محدودة", "100 GB تخزين", "طلبات AI غير محدودة", "دعم مخصص 24/7", "SLA", "نطاق مخصص", "SSO"]')
ON CONFLICT (code) DO NOTHING;

-- Free plan limits
INSERT INTO public.plan_limits (plan_id, key, value, period) VALUES
    ((SELECT id FROM public.plans WHERE code = 'free'), 'seats_max',             3,     'none'),
    ((SELECT id FROM public.plans WHERE code = 'free'), 'messages_per_month',    100,   'month'),
    ((SELECT id FROM public.plans WHERE code = 'free'), 'storage_mb',            500,   'none'),
    ((SELECT id FROM public.plans WHERE code = 'free'), 'ai_requests_per_month', 50,    'month')
ON CONFLICT (plan_id, key) DO NOTHING;

-- Pro plan limits
INSERT INTO public.plan_limits (plan_id, key, value, period) VALUES
    ((SELECT id FROM public.plans WHERE code = 'pro'), 'seats_max',             25,     'none'),
    ((SELECT id FROM public.plans WHERE code = 'pro'), 'messages_per_month',    5000,   'month'),
    ((SELECT id FROM public.plans WHERE code = 'pro'), 'storage_mb',            10000,  'none'),
    ((SELECT id FROM public.plans WHERE code = 'pro'), 'ai_requests_per_month', 2000,   'month')
ON CONFLICT (plan_id, key) DO NOTHING;

-- Enterprise plan limits (-1 = unlimited)
INSERT INTO public.plan_limits (plan_id, key, value, period) VALUES
    ((SELECT id FROM public.plans WHERE code = 'enterprise'), 'seats_max',             -1,      'none'),
    ((SELECT id FROM public.plans WHERE code = 'enterprise'), 'messages_per_month',    -1,      'month'),
    ((SELECT id FROM public.plans WHERE code = 'enterprise'), 'storage_mb',            100000,  'none'),
    ((SELECT id FROM public.plans WHERE code = 'enterprise'), 'ai_requests_per_month', -1,      'month')
ON CONFLICT (plan_id, key) DO NOTHING;

-- ============================================================
-- DONE. Schema is ready.
-- ============================================================


-- <<< END schema_final.sql <<<

-- >>> BEGIN migration_v3_invitations_platform.sql >>>

-- ============================================================
-- Migration V3: Digital Invitations Platform
-- منصة إدارة الدعوات الرقمية
-- ============================================================
-- New tables: teams, team_memberships, event_categories,
--   event_types, events, invite_templates, template_assets,
--   template_elements, guests, invitations, invitation_deliveries,
--   checkins
-- New enums: ticket_class, invitation_status, delivery_channel,
--   template_type, element_type, rsvp_status, checkin_result
-- ============================================================

-- ============================================================
-- 1) NEW ENUMS
-- ============================================================

CREATE TYPE ticket_class AS ENUM ('vip', 'normal');
CREATE TYPE invitation_status AS ENUM ('created', 'sent', 'viewed', 'accepted', 'declined', 'checked_in', 'revoked', 'expired');
CREATE TYPE delivery_channel AS ENUM ('sms', 'email', 'whatsapp', 'link', 'print');
CREATE TYPE template_type AS ENUM ('quick', 'designed');
CREATE TYPE element_type AS ENUM ('guest_name', 'event_title', 'event_date', 'event_time', 'event_location', 'qr_code', 'barcode', 'seat_number', 'gate', 'hall', 'table_number', 'custom_text', 'image');
CREATE TYPE rsvp_status AS ENUM ('pending', 'accepted', 'declined', 'maybe');
CREATE TYPE checkin_result AS ENUM ('success', 'already_checked_in', 'revoked', 'expired', 'invalid', 'wrong_event', 'wrong_gate');

-- ============================================================
-- 2) TEAMS (فرق داخل المؤسسة)
-- ============================================================

CREATE TABLE public.teams (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id   UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    description TEXT,
    color       TEXT DEFAULT '#6366f1',
    is_active   BOOLEAN NOT NULL DEFAULT true,
    created_by  UUID REFERENCES public.profiles(id),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(tenant_id, name)
);

CREATE INDEX idx_teams_tenant_id ON public.teams(tenant_id);

-- ============================================================
-- 3) TEAM MEMBERSHIPS (عضوية الفرق)
-- ============================================================

CREATE TABLE public.team_memberships (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    team_id     UUID NOT NULL REFERENCES public.teams(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    role        TEXT NOT NULL DEFAULT 'member',  -- team_lead, member
    joined_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(team_id, user_id)
);

CREATE INDEX idx_team_memberships_team_id ON public.team_memberships(team_id);
CREATE INDEX idx_team_memberships_user_id ON public.team_memberships(user_id);

-- ============================================================
-- 4) EVENT CATEGORIES (تصنيفات الأحداث)
-- ============================================================

CREATE TABLE public.event_categories (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id   UUID REFERENCES public.tenants(id) ON DELETE CASCADE,  -- NULL = system-wide
    name        TEXT NOT NULL,
    name_ar     TEXT,
    icon        TEXT,
    color       TEXT DEFAULT '#6366f1',
    sort_order  INT NOT NULL DEFAULT 0,
    is_system   BOOLEAN NOT NULL DEFAULT false,
    is_active   BOOLEAN NOT NULL DEFAULT true,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_event_categories_tenant ON public.event_categories(tenant_id);

-- ============================================================
-- 5) EVENT TYPES (أنواع تفصيلية تحت التصنيف)
-- ============================================================

CREATE TABLE public.event_types (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    category_id     UUID NOT NULL REFERENCES public.event_categories(id) ON DELETE CASCADE,
    tenant_id       UUID REFERENCES public.tenants(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    name_ar         TEXT,
    description     TEXT,
    is_system       BOOLEAN NOT NULL DEFAULT false,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_event_types_category ON public.event_types(category_id);
CREATE INDEX idx_event_types_tenant ON public.event_types(tenant_id);

-- ============================================================
-- 6) EVENTS (الأحداث/الاحتفالات)
-- ============================================================

CREATE TABLE public.events (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    event_type_id   UUID REFERENCES public.event_types(id),
    category_id     UUID REFERENCES public.event_categories(id),

    -- Basic info
    title           TEXT NOT NULL,
    title_ar        TEXT,
    description     TEXT,
    slug            TEXT,

    -- Date & Time
    start_date      TIMESTAMPTZ NOT NULL,
    end_date        TIMESTAMPTZ,
    timezone        TEXT NOT NULL DEFAULT 'Asia/Riyadh',

    -- Location
    venue_name      TEXT,
    venue_name_ar   TEXT,
    venue_address   TEXT,
    venue_city      TEXT,
    venue_country   TEXT DEFAULT 'SA',
    venue_map_url   TEXT,
    venue_lat       DECIMAL(10, 8),
    venue_lng       DECIMAL(11, 8),

    -- Invitation settings
    vip_quota       INT NOT NULL DEFAULT 0,
    normal_quota    INT NOT NULL DEFAULT 100,
    allow_rsvp      BOOLEAN NOT NULL DEFAULT false,
    allow_plus_one  BOOLEAN NOT NULL DEFAULT false,
    allow_reentry   BOOLEAN NOT NULL DEFAULT false,
    require_name    BOOLEAN NOT NULL DEFAULT true,

    -- Design
    cover_image_url TEXT,
    theme_color     TEXT DEFAULT '#6366f1',

    -- Status
    status          TEXT NOT NULL DEFAULT 'draft',  -- draft, published, active, completed, cancelled
    published_at    TIMESTAMPTZ,

    -- Meta
    created_by      UUID REFERENCES public.profiles(id),
    team_id         UUID REFERENCES public.teams(id),
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_events_tenant_id ON public.events(tenant_id);
CREATE INDEX idx_events_status ON public.events(status);
CREATE INDEX idx_events_start_date ON public.events(start_date);
CREATE INDEX idx_events_category ON public.events(category_id);
CREATE INDEX idx_events_type ON public.events(event_type_id);
CREATE INDEX idx_events_team ON public.events(team_id);
CREATE INDEX idx_events_slug ON public.events(tenant_id, slug);

-- ============================================================
-- 7) EVENT GATES (بوابات الدخول للحدث)
-- ============================================================

CREATE TABLE public.event_gates (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id    UUID NOT NULL REFERENCES public.events(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    name_ar     TEXT,
    allowed_classes ticket_class[] DEFAULT '{normal,vip}',
    is_active   BOOLEAN NOT NULL DEFAULT true,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_event_gates_event ON public.event_gates(event_id);

-- ============================================================
-- 8) INVITE TEMPLATES (قوالب الدعوات)
-- ============================================================

CREATE TABLE public.invite_templates (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    event_id        UUID REFERENCES public.events(id) ON DELETE SET NULL,

    name            TEXT NOT NULL,
    template_type   template_type NOT NULL DEFAULT 'quick',
    ticket_class    ticket_class NOT NULL DEFAULT 'normal',

    -- Design dimensions (for designed templates)
    width_px        INT DEFAULT 1080,
    height_px       INT DEFAULT 1920,
    orientation     TEXT DEFAULT 'portrait',  -- portrait, landscape

    -- Background
    background_url  TEXT,
    background_color TEXT DEFAULT '#ffffff',

    -- Quick template settings
    quick_style     JSONB DEFAULT '{}',  -- {layout, colorScheme, fontFamily, showQR, showName, showDate}

    -- Status
    is_default      BOOLEAN NOT NULL DEFAULT false,
    is_active       BOOLEAN NOT NULL DEFAULT true,

    created_by      UUID REFERENCES public.profiles(id),
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_invite_templates_tenant ON public.invite_templates(tenant_id);
CREATE INDEX idx_invite_templates_event ON public.invite_templates(event_id);
CREATE INDEX idx_invite_templates_type ON public.invite_templates(template_type);

-- ============================================================
-- 9) TEMPLATE ELEMENTS (عناصر التصميم + إحداثيات نسبية)
-- ============================================================

CREATE TABLE public.template_elements (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_id     UUID NOT NULL REFERENCES public.invite_templates(id) ON DELETE CASCADE,

    element_type    element_type NOT NULL,
    label           TEXT,  -- display label in editor

    -- Position (relative 0..1)
    x               DECIMAL(6, 4) NOT NULL DEFAULT 0.5,
    y               DECIMAL(6, 4) NOT NULL DEFAULT 0.5,
    width           DECIMAL(6, 4) NOT NULL DEFAULT 0.2,
    height          DECIMAL(6, 4) NOT NULL DEFAULT 0.05,
    rotation        DECIMAL(6, 2) DEFAULT 0,

    -- Text styling
    font_family     TEXT DEFAULT 'Cairo',
    font_size       DECIMAL(6, 2) DEFAULT 24,
    font_weight     TEXT DEFAULT 'normal',  -- normal, bold
    font_color      TEXT DEFAULT '#000000',
    text_align      TEXT DEFAULT 'center',  -- left, center, right
    text_direction  TEXT DEFAULT 'rtl',     -- rtl, ltr
    line_height     DECIMAL(4, 2) DEFAULT 1.2,
    letter_spacing  DECIMAL(4, 2) DEFAULT 0,

    -- QR/Barcode styling
    qr_size         DECIMAL(6, 4) DEFAULT 0.15,
    qr_color        TEXT DEFAULT '#000000',
    qr_bg_color     TEXT DEFAULT '#ffffff',
    qr_error_level  TEXT DEFAULT 'M',  -- L, M, Q, H

    -- Custom text content (for custom_text type)
    static_content  TEXT,

    -- Visibility & ordering
    is_visible      BOOLEAN NOT NULL DEFAULT true,
    z_index         INT NOT NULL DEFAULT 0,
    sort_order      INT NOT NULL DEFAULT 0,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_template_elements_template ON public.template_elements(template_id);

-- ============================================================
-- 10) TEMPLATE ASSETS (ملفات التصميم: خلفيات، خطوط)
-- ============================================================

CREATE TABLE public.template_assets (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_id     UUID NOT NULL REFERENCES public.invite_templates(id) ON DELETE CASCADE,
    asset_type      TEXT NOT NULL,  -- background, font, overlay, logo, stamp
    file_url        TEXT NOT NULL,
    file_name       TEXT,
    file_size       BIGINT DEFAULT 0,
    mime_type       TEXT,
    metadata        JSONB DEFAULT '{}',
    sort_order      INT DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_template_assets_template ON public.template_assets(template_id);

-- ============================================================
-- 11) GUESTS (دفتر الضيوف)
-- ============================================================

CREATE TABLE public.guests (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,

    full_name       TEXT NOT NULL,
    full_name_ar    TEXT,
    phone           TEXT,
    email           TEXT,
    company         TEXT,
    title           TEXT,  -- Mr, Mrs, Dr, Sheikh, etc.
    notes           TEXT,
    tags            TEXT[] DEFAULT '{}',

    metadata        JSONB DEFAULT '{}',
    created_by      UUID REFERENCES public.profiles(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_guests_tenant ON public.guests(tenant_id);
CREATE INDEX idx_guests_phone ON public.guests(phone);
CREATE INDEX idx_guests_email ON public.guests(email);
CREATE INDEX idx_guests_name ON public.guests(tenant_id, full_name);

-- ============================================================
-- 12) INVITATIONS (الدعوات)
-- ============================================================

CREATE TABLE public.invitations (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    event_id        UUID NOT NULL REFERENCES public.events(id) ON DELETE CASCADE,
    template_id     UUID REFERENCES public.invite_templates(id),
    guest_id        UUID REFERENCES public.guests(id),

    -- Invitation info
    ticket_class    ticket_class NOT NULL DEFAULT 'normal',
    status          invitation_status NOT NULL DEFAULT 'created',

    -- Token & QR
    token           TEXT NOT NULL UNIQUE DEFAULT encode(gen_random_bytes(16), 'hex'),
    qr_data         TEXT,  -- what's encoded in QR (usually the token or a URL)
    short_url       TEXT,

    -- Guest info (denormalized for quick invites without guest record)
    guest_name      TEXT,
    guest_count     INT NOT NULL DEFAULT 1,
    guest_name_ar   TEXT,
    guest_phone     TEXT,
    guest_email     TEXT,

    -- Seating
    seat_number     TEXT,
    table_number    TEXT,
    gate_id         UUID REFERENCES public.event_gates(id),
    hall            TEXT,
    zone            TEXT,

    -- RSVP
    rsvp_status     rsvp_status DEFAULT 'pending',
    rsvp_at         TIMESTAMPTZ,
    plus_one_count  INT DEFAULT 0,
    rsvp_message    TEXT,

    -- Check-in
    checked_in_at   TIMESTAMPTZ,
    checked_in_by   UUID REFERENCES public.profiles(id),
    checkin_count   INT NOT NULL DEFAULT 0,

    -- Generated card
    card_image_url  TEXT,
    card_pdf_url    TEXT,

    -- Meta
    notes           TEXT,
    metadata        JSONB DEFAULT '{}',
    created_by      UUID REFERENCES public.profiles(id),
    expires_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_invitations_tenant ON public.invitations(tenant_id);
CREATE INDEX idx_invitations_event ON public.invitations(event_id);
CREATE INDEX idx_invitations_token ON public.invitations(token);
CREATE INDEX idx_invitations_status ON public.invitations(status);
CREATE INDEX idx_invitations_ticket_class ON public.invitations(ticket_class);
CREATE INDEX idx_invitations_guest ON public.invitations(guest_id);
CREATE INDEX idx_invitations_event_class ON public.invitations(event_id, ticket_class);
CREATE INDEX idx_invitations_event_status ON public.invitations(event_id, status);

-- ============================================================
-- 13) INVITATION DELIVERIES (سجل الإرسال)
-- ============================================================

CREATE TABLE public.invitation_deliveries (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    invitation_id   UUID NOT NULL REFERENCES public.invitations(id) ON DELETE CASCADE,
    channel         delivery_channel NOT NULL,
    recipient       TEXT NOT NULL,  -- phone number, email, etc.
    status          TEXT NOT NULL DEFAULT 'pending',  -- pending, sent, delivered, failed, bounced
    provider        TEXT,  -- twilio, sendgrid, etc.
    provider_id     TEXT,  -- external message ID
    error_message   TEXT,
    sent_at         TIMESTAMPTZ,
    delivered_at    TIMESTAMPTZ,
    opened_at       TIMESTAMPTZ,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_invitation_deliveries_invitation ON public.invitation_deliveries(invitation_id);
CREATE INDEX idx_invitation_deliveries_status ON public.invitation_deliveries(status);
CREATE INDEX idx_invitation_deliveries_channel ON public.invitation_deliveries(channel);

-- ============================================================
-- 14) CHECKINS (سجل الدخول)
-- ============================================================

CREATE TABLE public.checkins (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    invitation_id   UUID REFERENCES public.invitations(id) ON DELETE CASCADE,
    event_id        UUID NOT NULL REFERENCES public.events(id) ON DELETE CASCADE,
    gate_id         UUID REFERENCES public.event_gates(id),

    result          checkin_result NOT NULL,
    scanned_by      UUID REFERENCES public.profiles(id),
    scan_method     TEXT DEFAULT 'qr',  -- qr, manual, nfc
    device_info     TEXT,
    ip_address      INET,

    notes           TEXT,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_checkins_invitation ON public.checkins(invitation_id);
CREATE INDEX idx_checkins_event ON public.checkins(event_id);
CREATE INDEX idx_checkins_result ON public.checkins(result);
CREATE INDEX idx_checkins_created ON public.checkins(created_at DESC);

-- ============================================================
-- 15) TRIGGERS: updated_at
-- ============================================================

CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.teams
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.events
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.invite_templates
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.guests
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.invitations
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

-- ============================================================
-- 16) RLS: Enable on all new tables
-- ============================================================

ALTER TABLE public.teams ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.team_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.event_categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.event_types ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.event_gates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.invite_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.template_elements ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.template_assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.guests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.invitations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.invitation_deliveries ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.checkins ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- 17) RLS POLICIES
-- ============================================================

-- ── Teams ──
CREATE POLICY "Members can view teams" ON public.teams
    FOR SELECT USING (tenant_id IN (SELECT public.get_my_tenant_ids()));
CREATE POLICY "Admins can manage teams" ON public.teams
    FOR ALL USING (public.is_admin_of(tenant_id));

-- ── Team Memberships ──
CREATE POLICY "Members can view team memberships" ON public.team_memberships
    FOR SELECT USING (
        team_id IN (SELECT id FROM public.teams WHERE tenant_id IN (SELECT public.get_my_tenant_ids()))
    );
CREATE POLICY "Admins can manage team memberships" ON public.team_memberships
    FOR ALL USING (
        team_id IN (SELECT id FROM public.teams WHERE public.is_admin_of(tenant_id))
    );

-- ── Event Categories ──
CREATE POLICY "Anyone can view event categories" ON public.event_categories
    FOR SELECT USING (
        is_system = true
        OR tenant_id IS NULL
        OR tenant_id IN (SELECT public.get_my_tenant_ids())
    );
CREATE POLICY "Admins can manage event categories" ON public.event_categories
    FOR ALL USING (tenant_id IS NOT NULL AND public.is_admin_of(tenant_id));

-- ── Event Types ──
CREATE POLICY "Anyone can view event types" ON public.event_types
    FOR SELECT USING (
        is_system = true
        OR tenant_id IS NULL
        OR tenant_id IN (SELECT public.get_my_tenant_ids())
    );
CREATE POLICY "Admins can manage event types" ON public.event_types
    FOR ALL USING (tenant_id IS NOT NULL AND public.is_admin_of(tenant_id));

-- ── Events ──
CREATE POLICY "Members can view events" ON public.events
    FOR SELECT USING (tenant_id IN (SELECT public.get_my_tenant_ids()));
CREATE POLICY "Admins can manage events" ON public.events
    FOR ALL USING (public.is_admin_of(tenant_id));

-- ── Event Gates ──
CREATE POLICY "Members can view gates" ON public.event_gates
    FOR SELECT USING (
        event_id IN (SELECT id FROM public.events WHERE tenant_id IN (SELECT public.get_my_tenant_ids()))
    );
CREATE POLICY "Admins can manage gates" ON public.event_gates
    FOR ALL USING (
        event_id IN (SELECT id FROM public.events WHERE public.is_admin_of(tenant_id))
    );

-- ── Invite Templates ──
CREATE POLICY "Members can view templates" ON public.invite_templates
    FOR SELECT USING (tenant_id IN (SELECT public.get_my_tenant_ids()));
CREATE POLICY "Admins can manage templates" ON public.invite_templates
    FOR ALL USING (public.is_admin_of(tenant_id));

-- ── Template Elements ──
CREATE POLICY "Members can view template elements" ON public.template_elements
    FOR SELECT USING (
        template_id IN (SELECT id FROM public.invite_templates WHERE tenant_id IN (SELECT public.get_my_tenant_ids()))
    );
CREATE POLICY "Admins can manage template elements" ON public.template_elements
    FOR ALL USING (
        template_id IN (SELECT id FROM public.invite_templates WHERE public.is_admin_of(tenant_id))
    );

-- ── Template Assets ──
CREATE POLICY "Members can view template assets" ON public.template_assets
    FOR SELECT USING (
        template_id IN (SELECT id FROM public.invite_templates WHERE tenant_id IN (SELECT public.get_my_tenant_ids()))
    );
CREATE POLICY "Admins can manage template assets" ON public.template_assets
    FOR ALL USING (
        template_id IN (SELECT id FROM public.invite_templates WHERE public.is_admin_of(tenant_id))
    );

-- ── Guests ──
CREATE POLICY "Members can view guests" ON public.guests
    FOR SELECT USING (tenant_id IN (SELECT public.get_my_tenant_ids()));
CREATE POLICY "Admins can manage guests" ON public.guests
    FOR ALL USING (public.is_admin_of(tenant_id));

-- ── Invitations ──
CREATE POLICY "Members can view invitations" ON public.invitations
    FOR SELECT USING (tenant_id IN (SELECT public.get_my_tenant_ids()));
CREATE POLICY "Admins can manage invitations" ON public.invitations
    FOR ALL USING (public.is_admin_of(tenant_id));

-- ── Invitation Deliveries ──
CREATE POLICY "Members can view deliveries" ON public.invitation_deliveries
    FOR SELECT USING (
        invitation_id IN (SELECT id FROM public.invitations WHERE tenant_id IN (SELECT public.get_my_tenant_ids()))
    );

-- ── Checkins ──
CREATE POLICY "Members can view checkins" ON public.checkins
    FOR SELECT USING (
        event_id IN (SELECT id FROM public.events WHERE tenant_id IN (SELECT public.get_my_tenant_ids()))
    );
CREATE POLICY "Staff can insert checkins" ON public.checkins
    FOR INSERT WITH CHECK (
        event_id IN (SELECT id FROM public.events WHERE tenant_id IN (SELECT public.get_my_tenant_ids()))
    );

-- ============================================================
-- 18) NEW PERMISSIONS FOR INVITATION PLATFORM
-- ============================================================

INSERT INTO public.permissions (key, description) VALUES
    ('events.create',       'إنشاء حدث جديد'),
    ('events.view',         'عرض الأحداث'),
    ('events.edit',         'تعديل حدث'),
    ('events.delete',       'حذف حدث'),
    ('events.publish',      'نشر حدث'),
    ('templates.view',      'عرض القوالب'),
    ('templates.create',    'إنشاء قالب'),
    ('templates.edit',      'تعديل قالب'),
    ('templates.delete',    'حذف قالب'),
    ('invitations.create',  'إنشاء دعوات'),
    ('invitations.view',    'عرض الدعوات'),
    ('invitations.send',    'إرسال دعوات'),
    ('invitations.revoke',  'إلغاء دعوات'),
    ('invitations.export',  'تصدير دعوات'),
    ('guests.view',         'عرض الضيوف'),
    ('guests.create',       'إضافة ضيف'),
    ('guests.edit',         'تعديل ضيف'),
    ('guests.delete',       'حذف ضيف'),
    ('guests.import',       'استيراد ضيوف'),
    ('checkin.scan',        'مسح QR للدخول'),
    ('checkin.view',        'عرض سجل الدخول'),
    ('checkin.manual',      'تسجيل دخول يدوي'),
    ('teams.view',          'عرض الفرق'),
    ('teams.manage',        'إدارة الفرق'),
    ('gates.view',          'عرض البوابات'),
    ('gates.manage',        'إدارة البوابات')
ON CONFLICT (key) DO NOTHING;

-- ============================================================
-- 19) UPDATE PLAN LIMITS FOR INVITATION PLATFORM
-- ============================================================

-- Add new limit keys for existing plans
INSERT INTO public.plan_limits (plan_id, key, value, period) VALUES
    -- Free plan
    ((SELECT id FROM plans WHERE code = 'free'), 'events_per_month',        1,     'month'),
    ((SELECT id FROM plans WHERE code = 'free'), 'invitations_per_event',   50,    'none'),
    ((SELECT id FROM plans WHERE code = 'free'), 'invitations_per_month',   50,    'month'),
    ((SELECT id FROM plans WHERE code = 'free'), 'teams_max',               1,     'none'),
    ((SELECT id FROM plans WHERE code = 'free'), 'designed_templates',      0,     'none'),
    ((SELECT id FROM plans WHERE code = 'free'), 'gates_per_event',         1,     'none'),
    -- Pro plan
    ((SELECT id FROM plans WHERE code = 'pro'), 'events_per_month',         20,    'month'),
    ((SELECT id FROM plans WHERE code = 'pro'), 'invitations_per_event',    5000,  'none'),
    ((SELECT id FROM plans WHERE code = 'pro'), 'invitations_per_month',    10000, 'month'),
    ((SELECT id FROM plans WHERE code = 'pro'), 'teams_max',                5,     'none'),
    ((SELECT id FROM plans WHERE code = 'pro'), 'designed_templates',       -1,    'none'),
    ((SELECT id FROM plans WHERE code = 'pro'), 'gates_per_event',          5,     'none'),
    -- Enterprise plan
    ((SELECT id FROM plans WHERE code = 'enterprise'), 'events_per_month',       -1,    'month'),
    ((SELECT id FROM plans WHERE code = 'enterprise'), 'invitations_per_event',  -1,    'none'),
    ((SELECT id FROM plans WHERE code = 'enterprise'), 'invitations_per_month',  -1,    'month'),
    ((SELECT id FROM plans WHERE code = 'enterprise'), 'teams_max',              -1,    'none'),
    ((SELECT id FROM plans WHERE code = 'enterprise'), 'designed_templates',     -1,    'none'),
    ((SELECT id FROM plans WHERE code = 'enterprise'), 'gates_per_event',        -1,    'none')
ON CONFLICT (plan_id, key) DO NOTHING;

-- Update plan features descriptions
UPDATE public.plans SET features = '["حدث واحد/شهر", "50 دعوة", "دعوات سريعة فقط", "بوابة واحدة", "3 أعضاء"]'::jsonb WHERE code = 'free';
UPDATE public.plans SET features = '["20 حدث/شهر", "5,000 دعوة/حدث", "تصميم بإحداثيات", "5 بوابات", "5 فرق", "25 عضو", "RSVP", "تقارير متقدمة"]'::jsonb WHERE code = 'pro';
UPDATE public.plans SET features = '["أحداث غير محدودة", "دعوات غير محدودة", "تصميم بإحداثيات", "بوابات غير محدودة", "فرق غير محدودة", "أعضاء غير محدود", "RSVP", "SSO", "SLA", "دعم مخصص 24/7"]'::jsonb WHERE code = 'enterprise';

-- ============================================================
-- 20) SEED: DEFAULT EVENT CATEGORIES & TYPES
-- ============================================================

-- System-wide categories (tenant_id = NULL)
INSERT INTO public.event_categories (name, name_ar, icon, color, sort_order, is_system) VALUES
    ('Graduation',  'تخرج',    'graduation-cap', '#8b5cf6', 1, true),
    ('Wedding',     'زفاف',    'heart',           '#ec4899', 2, true),
    ('Conference',  'مؤتمر',   'presentation',    '#3b82f6', 3, true),
    ('Corporate',   'شركات',   'building',        '#6366f1', 4, true),
    ('Birthday',    'عيد ميلاد','cake',            '#f59e0b', 5, true),
    ('Religious',   'ديني',    'moon',            '#10b981', 6, true),
    ('Social',      'اجتماعي', 'users',           '#06b6d4', 7, true),
    ('Other',       'أخرى',    'calendar',        '#64748b', 99, true);

-- Default event types under each category
INSERT INTO public.event_types (category_id, name, name_ar, is_system) VALUES
    -- Graduation
    ((SELECT id FROM event_categories WHERE name = 'Graduation'), 'University Graduation', 'تخرج جامعي', true),
    ((SELECT id FROM event_categories WHERE name = 'Graduation'), 'High School Graduation', 'تخرج ثانوي', true),
    ((SELECT id FROM event_categories WHERE name = 'Graduation'), 'Training Completion', 'إتمام تدريب', true),
    -- Wedding
    ((SELECT id FROM event_categories WHERE name = 'Wedding'), 'Wedding Ceremony', 'حفل زفاف', true),
    ((SELECT id FROM event_categories WHERE name = 'Wedding'), 'Engagement Party', 'حفل خطوبة', true),
    ((SELECT id FROM event_categories WHERE name = 'Wedding'), 'Henna Night', 'ليلة حناء', true),
    -- Conference
    ((SELECT id FROM event_categories WHERE name = 'Conference'), 'Tech Conference', 'مؤتمر تقني', true),
    ((SELECT id FROM event_categories WHERE name = 'Conference'), 'Medical Conference', 'مؤتمر طبي', true),
    ((SELECT id FROM event_categories WHERE name = 'Conference'), 'Workshop', 'ورشة عمل', true),
    ((SELECT id FROM event_categories WHERE name = 'Conference'), 'Seminar', 'ندوة', true),
    -- Corporate
    ((SELECT id FROM event_categories WHERE name = 'Corporate'), 'Company Event', 'حفل شركة', true),
    ((SELECT id FROM event_categories WHERE name = 'Corporate'), 'Product Launch', 'إطلاق منتج', true),
    ((SELECT id FROM event_categories WHERE name = 'Corporate'), 'Annual Meeting', 'اجتماع سنوي', true),
    -- Birthday
    ((SELECT id FROM event_categories WHERE name = 'Birthday'), 'Birthday Party', 'حفل عيد ميلاد', true),
    ((SELECT id FROM event_categories WHERE name = 'Birthday'), 'Kids Party', 'حفل أطفال', true),
    -- Religious
    ((SELECT id FROM event_categories WHERE name = 'Religious'), 'Iftar', 'إفطار رمضاني', true),
    ((SELECT id FROM event_categories WHERE name = 'Religious'), 'Eid Celebration', 'احتفال عيد', true),
    -- Social
    ((SELECT id FROM event_categories WHERE name = 'Social'), 'Gathering', 'تجمع', true),
    ((SELECT id FROM event_categories WHERE name = 'Social'), 'Charity Event', 'حفل خيري', true),
    -- Other
    ((SELECT id FROM event_categories WHERE name = 'Other'), 'Custom Event', 'حدث مخصص', true);

-- ============================================================
-- 21) UPDATE PROVISIONING: add invitation platform defaults
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
    v_checkin_role_id UUID;
    v_designer_role_id UUID;
BEGIN
    -- Create Admin role (all permissions)
    INSERT INTO public.roles (tenant_id, name, description, is_system_role)
    VALUES (p_tenant_id, 'Admin', 'مدير كامل الصلاحيات', true)
    RETURNING id INTO v_admin_role_id;

    INSERT INTO public.role_permissions (role_id, permission_key)
    SELECT v_admin_role_id, key FROM public.permissions;

    -- Create Event Manager role
    INSERT INTO public.roles (tenant_id, name, description, is_system_role)
    VALUES (p_tenant_id, 'Member', 'مدير أحداث ودعوات', true)
    RETURNING id INTO v_member_role_id;

    INSERT INTO public.role_permissions (role_id, permission_key)
    SELECT v_member_role_id, key FROM public.permissions
    WHERE key IN (
        'users.view', 'members.view', 'settings.view', 'reports.view',
        'files.upload', 'files.view', 'notifications.view', 'tenant.view',
        'events.create', 'events.view', 'events.edit',
        'templates.view', 'templates.create', 'templates.edit',
        'invitations.create', 'invitations.view', 'invitations.send',
        'guests.view', 'guests.create', 'guests.edit', 'guests.import',
        'checkin.scan', 'checkin.view',
        'teams.view', 'gates.view'
    );

    -- Create Designer role
    INSERT INTO public.roles (tenant_id, name, description, is_system_role)
    VALUES (p_tenant_id, 'Designer', 'مصمم القوالب', true)
    RETURNING id INTO v_designer_role_id;

    INSERT INTO public.role_permissions (role_id, permission_key)
    SELECT v_designer_role_id, key FROM public.permissions
    WHERE key IN (
        'templates.view', 'templates.create', 'templates.edit',
        'files.upload', 'files.view',
        'events.view', 'invitations.view',
        'tenant.view'
    );

    -- Create Check-in Staff role
    INSERT INTO public.roles (tenant_id, name, description, is_system_role)
    VALUES (p_tenant_id, 'Check-in Staff', 'موظف استقبال ومسح', true)
    RETURNING id INTO v_checkin_role_id;

    INSERT INTO public.role_permissions (role_id, permission_key)
    SELECT v_checkin_role_id, key FROM public.permissions
    WHERE key IN (
        'checkin.scan', 'checkin.view', 'checkin.manual',
        'events.view', 'invitations.view', 'guests.view',
        'gates.view', 'tenant.view'
    );

    -- Create Viewer role (read-only)
    INSERT INTO public.roles (tenant_id, name, description, is_system_role)
    VALUES (p_tenant_id, 'Viewer', 'مشاهد فقط', true)
    RETURNING id INTO v_viewer_role_id;

    INSERT INTO public.role_permissions (role_id, permission_key)
    SELECT v_viewer_role_id, key FROM public.permissions
    WHERE key IN (
        'users.view', 'members.view', 'reports.view',
        'files.view', 'notifications.view', 'tenant.view',
        'events.view', 'invitations.view', 'guests.view',
        'checkin.view', 'templates.view', 'teams.view', 'gates.view'
    );

    -- Assign Admin role to the owner
    INSERT INTO public.membership_roles (tenant_id, user_id, role_id)
    VALUES (p_tenant_id, p_owner_user_id, v_admin_role_id)
    ON CONFLICT DO NOTHING;

    -- Set default tenant settings
    INSERT INTO public.tenant_settings (tenant_id, key, value) VALUES
        (p_tenant_id, 'timezone',                '"Asia/Riyadh"'),
        (p_tenant_id, 'language',                '"ar"'),
        (p_tenant_id, 'date_format',             '"YYYY-MM-DD"'),
        (p_tenant_id, 'time_format',             '"HH:mm"'),
        (p_tenant_id, 'logo_url',                '""'),
        (p_tenant_id, 'favicon_url',             '""'),
        (p_tenant_id, 'primary_color',           '"#6366f1"'),
        (p_tenant_id, 'secondary_color',         '"#8b5cf6"'),
        (p_tenant_id, 'company_email',           '""'),
        (p_tenant_id, 'company_phone',           '""'),
        (p_tenant_id, 'company_address',         '""'),
        (p_tenant_id, 'currency',                '"SAR"'),
        (p_tenant_id, 'notifications_enabled',   'true'),
        (p_tenant_id, 'email_notifications',     'true'),
        (p_tenant_id, 'sms_notifications',       'false'),
        (p_tenant_id, 'two_factor_required',     'false'),
        (p_tenant_id, 'session_timeout_minutes', '60'),
        (p_tenant_id, 'max_login_attempts',      '5'),
        (p_tenant_id, 'default_ticket_class',    '"normal"'),
        (p_tenant_id, 'default_invitation_expiry_days', '30'),
        (p_tenant_id, 'allow_reentry_default',   'false'),
        (p_tenant_id, 'checkin_sound_enabled',   'true'),
        (p_tenant_id, 'invitation_sms_template', '""'),
        (p_tenant_id, 'invitation_email_template','""')
    ON CONFLICT DO NOTHING;

    -- Set default feature flags
    INSERT INTO public.feature_flags (tenant_id, flag_key, enabled, metadata) VALUES
        (p_tenant_id, 'designed_templates',  false, '{"description": "قوالب بتصميم وإحداثيات"}'),
        (p_tenant_id, 'rsvp',               false, '{"description": "تأكيد الحضور RSVP"}'),
        (p_tenant_id, 'multi_gate',          false, '{"description": "بوابات متعددة"}'),
        (p_tenant_id, 'sms_delivery',        false, '{"description": "إرسال SMS"}'),
        (p_tenant_id, 'whatsapp_delivery',   false, '{"description": "إرسال WhatsApp"}'),
        (p_tenant_id, 'email_delivery',      true,  '{"description": "إرسال بريد إلكتروني"}'),
        (p_tenant_id, 'pdf_export',          false, '{"description": "تصدير PDF عالي الجودة"}'),
        (p_tenant_id, 'bulk_import',         false, '{"description": "استيراد ضيوف جماعي"}'),
        (p_tenant_id, 'advanced_reports',    false, '{"description": "تقارير متقدمة"}'),
        (p_tenant_id, 'api_access',          false, '{"description": "الوصول لـ REST API"}'),
        (p_tenant_id, 'custom_domain',       false, '{"description": "نطاق مخصص"}'),
        (p_tenant_id, 'white_label',         false, '{"description": "إزالة العلامة التجارية"}'),
        (p_tenant_id, 'audit_log',           true,  '{"description": "سجل التدقيق"}'),
        (p_tenant_id, 'multi_language',      true,  '{"description": "دعم متعدد اللغات"}'),
        (p_tenant_id, 'seating_management',  false, '{"description": "إدارة المقاعد والطاولات"}'),
        (p_tenant_id, 'vip_invitations',     true,  '{"description": "دعوات VIP"}')
    ON CONFLICT DO NOTHING;
END;
$$;

-- ============================================================
-- 22) HELPER: Count invitations for quota check
-- ============================================================

CREATE OR REPLACE FUNCTION public.count_event_invitations(
    p_event_id UUID,
    p_ticket_class ticket_class DEFAULT NULL
)
RETURNS BIGINT
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT COUNT(*)
    FROM public.invitations
    WHERE event_id = p_event_id
      AND status NOT IN ('revoked', 'expired')
      AND (p_ticket_class IS NULL OR ticket_class = p_ticket_class);
$$;

-- ============================================================
-- 23) HELPER: Validate invitation for check-in
-- ============================================================

CREATE OR REPLACE FUNCTION public.validate_checkin(
    p_token TEXT,
    p_event_id UUID DEFAULT NULL,
    p_gate_id UUID DEFAULT NULL
)
RETURNS TABLE (
    invitation_id UUID,
    result checkin_result,
    guest_name TEXT,
    ticket_class ticket_class,
    event_title TEXT,
    checkin_count INT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_inv RECORD;
    v_result checkin_result;
BEGIN
    -- Find invitation
    SELECT i.*, e.title AS event_title, e.allow_reentry
    INTO v_inv
    FROM public.invitations i
    JOIN public.events e ON e.id = i.event_id
    WHERE i.token = p_token;

    IF NOT FOUND THEN
        RETURN QUERY SELECT NULL::UUID, 'invalid'::checkin_result, NULL::TEXT, NULL::ticket_class, NULL::TEXT, 0;
        RETURN;
    END IF;

    -- Check event match
    IF p_event_id IS NOT NULL AND v_inv.event_id != p_event_id THEN
        RETURN QUERY SELECT v_inv.id, 'wrong_event'::checkin_result, v_inv.guest_name, v_inv.ticket_class, v_inv.event_title, v_inv.checkin_count;
        RETURN;
    END IF;

    -- Check revoked
    IF v_inv.status = 'revoked' THEN
        RETURN QUERY SELECT v_inv.id, 'revoked'::checkin_result, v_inv.guest_name, v_inv.ticket_class, v_inv.event_title, v_inv.checkin_count;
        RETURN;
    END IF;

    -- Check expired
    IF v_inv.status = 'expired' OR (v_inv.expires_at IS NOT NULL AND v_inv.expires_at < now()) THEN
        RETURN QUERY SELECT v_inv.id, 'expired'::checkin_result, v_inv.guest_name, v_inv.ticket_class, v_inv.event_title, v_inv.checkin_count;
        RETURN;
    END IF;

    -- Check already checked in
    IF v_inv.checkin_count >= COALESCE(v_inv.guest_count, 1) AND NOT v_inv.allow_reentry THEN
        RETURN QUERY SELECT v_inv.id, 'already_checked_in'::checkin_result, v_inv.guest_name, v_inv.ticket_class, v_inv.event_title, v_inv.checkin_count;
        RETURN;
    END IF;

    -- Check gate class
    IF p_gate_id IS NOT NULL THEN
        IF NOT EXISTS (
            SELECT 1 FROM public.event_gates
            WHERE id = p_gate_id AND v_inv.ticket_class = ANY(allowed_classes)
        ) THEN
            RETURN QUERY SELECT v_inv.id, 'wrong_gate'::checkin_result, v_inv.guest_name, v_inv.ticket_class, v_inv.event_title, v_inv.checkin_count;
            RETURN;
        END IF;
    END IF;

    -- Success
    RETURN QUERY SELECT v_inv.id, 'success'::checkin_result, v_inv.guest_name, v_inv.ticket_class, v_inv.event_title, v_inv.checkin_count;
END;
$$;

-- ============================================================
-- DONE: Migration V3 complete
-- ============================================================


-- <<< END migration_v3_invitations_platform.sql <<<

-- >>> BEGIN migration_v4_generation_batches.sql >>>

-- ============================================================
-- Migration V4: Generation Batches + Asset Pipeline
-- نظام توليد الباركود والصور وPDF/ZIP
-- ============================================================
-- New tables: generation_batches, batch_items
-- New columns on invitations: barcode_svg_url, barcode_png_url,
--   render_image_url, barcode_payload, barcode_signature
-- New enum: batch_status
-- New permissions: batches.create, batches.view, batches.manage
-- ============================================================

-- ============================================================
-- 1) ENUM: batch_status
-- ============================================================

CREATE TYPE batch_status AS ENUM (
    'draft',      -- تم الإنشاء ولم يبدأ
    'queued',     -- في الانتظار
    'generating_barcodes',  -- توليد الباركود
    'rendering_images',     -- تركيب الصور (DESIGNED فقط)
    'generating_pdf',       -- إنشاء PDF
    'generating_zip',       -- إنشاء ZIP
    'ready',      -- جاهز للتحميل
    'failed',     -- فشل
    'cancelled'   -- ملغى
);

-- ============================================================
-- 2) TABLE: generation_batches (دفعات التوليد)
-- ============================================================

CREATE TABLE public.generation_batches (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    event_id        UUID NOT NULL REFERENCES public.events(id) ON DELETE CASCADE,
    template_id     UUID REFERENCES public.invite_templates(id),

    -- Batch config
    mode            template_type NOT NULL DEFAULT 'quick',  -- quick / designed
    ticket_class    ticket_class NOT NULL DEFAULT 'normal',

    -- Counts
    count_total     INT NOT NULL DEFAULT 0,
    count_done      INT NOT NULL DEFAULT 0,
    count_failed    INT NOT NULL DEFAULT 0,

    -- PDF layout settings
    layout_json     JSONB NOT NULL DEFAULT '{
        "page_size": "A4",
        "orientation": "portrait",
        "rows": 5,
        "cols": 5,
        "margin_top_mm": 10,
        "margin_bottom_mm": 10,
        "margin_left_mm": 10,
        "margin_right_mm": 10,
        "gap_x_mm": 2,
        "gap_y_mm": 2,
        "barcode_size_px": 400,
        "show_code_text": true,
        "show_guest_name": true,
        "dpi": 300
    }',

    -- Output settings
    output_formats  TEXT[] NOT NULL DEFAULT '{pdf,zip}',  -- pdf, zip, or both
    barcode_format  TEXT NOT NULL DEFAULT 'qr',           -- qr, barcode128, datamatrix

    -- Status & progress
    status          batch_status NOT NULL DEFAULT 'draft',
    progress        INT NOT NULL DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    error_message   TEXT,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,

    -- Result URLs (stored in Supabase Storage)
    result_pdf_url  TEXT,
    result_zip_url  TEXT,
    result_preview_urls TEXT[] DEFAULT '{}',  -- أول 5 صور للمعاينة

    -- Meta
    created_by      UUID REFERENCES public.profiles(id),
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_gen_batches_tenant ON public.generation_batches(tenant_id);
CREATE INDEX idx_gen_batches_event ON public.generation_batches(event_id);
CREATE INDEX idx_gen_batches_status ON public.generation_batches(status);
CREATE INDEX idx_gen_batches_created ON public.generation_batches(created_at DESC);

-- ============================================================
-- 3) TABLE: batch_items (عناصر الدفعة — تتبع مفصل)
-- ============================================================

CREATE TABLE public.batch_items (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    batch_id        UUID NOT NULL REFERENCES public.generation_batches(id) ON DELETE CASCADE,
    invitation_id   UUID NOT NULL REFERENCES public.invitations(id) ON DELETE CASCADE,

    -- Per-item status
    render_status   TEXT NOT NULL DEFAULT 'pending',  -- pending, done, failed, skipped
    error_message   TEXT,

    -- Per-item output
    barcode_url     TEXT,
    render_url      TEXT,

    -- Timing
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_batch_items_batch ON public.batch_items(batch_id);
CREATE INDEX idx_batch_items_invitation ON public.batch_items(invitation_id);
CREATE INDEX idx_batch_items_status ON public.batch_items(render_status);

-- ============================================================
-- 4) ADD COLUMNS TO invitations (أصول الباركود والصورة)
-- ============================================================

ALTER TABLE public.invitations
    ADD COLUMN IF NOT EXISTS barcode_svg_url   TEXT,
    ADD COLUMN IF NOT EXISTS barcode_png_url   TEXT,
    ADD COLUMN IF NOT EXISTS render_image_url  TEXT,
    ADD COLUMN IF NOT EXISTS barcode_payload   TEXT,
    ADD COLUMN IF NOT EXISTS barcode_signature TEXT;

-- Add data_key to template_elements for dynamic data resolution
-- data_key maps element to data source: invite.barcode_payload, guest.name, event.title, etc.
ALTER TABLE public.template_elements
    ADD COLUMN IF NOT EXISTS data_key TEXT;

-- Add custom_fields to guests for extra dynamic data (date1, date2, seat, etc.)
ALTER TABLE public.guests
    ADD COLUMN IF NOT EXISTS custom_fields JSONB DEFAULT '{}';

-- ============================================================
-- 5) TRIGGERS
-- ============================================================

CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.generation_batches
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

-- ============================================================
-- 6) RLS
-- ============================================================

ALTER TABLE public.generation_batches ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.batch_items ENABLE ROW LEVEL SECURITY;

-- Batches
CREATE POLICY "Members can view batches" ON public.generation_batches
    FOR SELECT USING (tenant_id IN (SELECT public.get_my_tenant_ids()));
CREATE POLICY "Admins can manage batches" ON public.generation_batches
    FOR ALL USING (public.is_admin_of(tenant_id));

-- Batch items
CREATE POLICY "Members can view batch items" ON public.batch_items
    FOR SELECT USING (
        batch_id IN (SELECT id FROM public.generation_batches WHERE tenant_id IN (SELECT public.get_my_tenant_ids()))
    );
CREATE POLICY "Admins can manage batch items" ON public.batch_items
    FOR ALL USING (
        batch_id IN (SELECT id FROM public.generation_batches WHERE public.is_admin_of(tenant_id))
    );

-- ============================================================
-- 7) NEW PERMISSIONS
-- ============================================================

INSERT INTO public.permissions (key, description) VALUES
    ('batches.create',  'إنشاء دفعة توليد'),
    ('batches.view',    'عرض دفعات التوليد'),
    ('batches.manage',  'إدارة دفعات التوليد (إلغاء/إعادة)')
ON CONFLICT (key) DO NOTHING;

-- Add to existing roles
-- Admin already gets all permissions
-- Member gets create + view
INSERT INTO public.role_permissions (role_id, permission_key)
SELECT r.id, p.key
FROM public.roles r, public.permissions p
WHERE r.is_system_role = true
  AND r.name = 'Admin'
  AND p.key IN ('batches.create', 'batches.view', 'batches.manage')
ON CONFLICT DO NOTHING;

INSERT INTO public.role_permissions (role_id, permission_key)
SELECT r.id, p.key
FROM public.roles r, public.permissions p
WHERE r.is_system_role = true
  AND r.name = 'Member'
  AND p.key IN ('batches.create', 'batches.view')
ON CONFLICT DO NOTHING;

INSERT INTO public.role_permissions (role_id, permission_key)
SELECT r.id, p.key
FROM public.roles r, public.permissions p
WHERE r.is_system_role = true
  AND r.name = 'Viewer'
  AND p.key IN ('batches.view')
ON CONFLICT DO NOTHING;

-- ============================================================
-- 8) STORAGE BUCKET (Supabase Storage)
-- ============================================================
-- Run this in Supabase Dashboard > Storage or via API:
-- CREATE BUCKET: 'invitations' (private)
-- Policies:
--   - Authenticated users can upload to their org path
--   - Service role can do everything

-- ============================================================
-- 9) HELPER: Update batch progress
-- ============================================================

CREATE OR REPLACE FUNCTION public.update_batch_progress(p_batch_id UUID)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_total INT;
    v_done INT;
    v_failed INT;
    v_progress INT;
BEGIN
    SELECT count_total INTO v_total FROM generation_batches WHERE id = p_batch_id;

    SELECT
        COUNT(*) FILTER (WHERE render_status = 'done'),
        COUNT(*) FILTER (WHERE render_status = 'failed')
    INTO v_done, v_failed
    FROM batch_items WHERE batch_id = p_batch_id;

    IF v_total > 0 THEN
        v_progress := ((v_done + v_failed) * 100) / v_total;
    ELSE
        v_progress := 0;
    END IF;

    UPDATE generation_batches
    SET count_done = v_done,
        count_failed = v_failed,
        progress = LEAST(v_progress, 100),
        updated_at = now()
    WHERE id = p_batch_id;
END;
$$;

-- ============================================================
-- DONE: Migration V4 complete
-- ============================================================


-- <<< END migration_v4_generation_batches.sql <<<

-- >>> BEGIN migration_v5_production_hardening.sql >>>

-- ============================================================
-- Migration V5: Production Hardening
-- تحسينات أمنية وأداء لبيئة الإنتاج
-- ============================================================
-- 1) Atomic check-in with SELECT FOR UPDATE (race condition fix)
-- 2) Batch state machine constraints
-- 3) Brute-force protection index
-- 4) Batch metrics columns
-- ============================================================

-- ============================================================
-- 1) ATOMIC CHECK-IN: SELECT ... FOR UPDATE
--    Prevents double check-in when multiple scanners hit
--    the same invitation simultaneously.
-- ============================================================

CREATE OR REPLACE FUNCTION public.validate_checkin(
    p_token TEXT,
    p_event_id UUID DEFAULT NULL,
    p_gate_id UUID DEFAULT NULL
)
RETURNS TABLE (
    invitation_id UUID,
    result checkin_result,
    guest_name TEXT,
    ticket_class ticket_class,
    event_title TEXT,
    checkin_count INT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_inv RECORD;
    v_result checkin_result;
BEGIN
    -- Lock the invitation row to prevent concurrent check-in race conditions.
    -- FOR UPDATE ensures only one transaction can validate+update at a time.
    SELECT i.*, e.title AS event_title, e.allow_reentry
    INTO v_inv
    FROM public.invitations i
    JOIN public.events e ON e.id = i.event_id
    WHERE i.token = p_token
    FOR UPDATE OF i;  -- row-level lock on invitations only

    IF NOT FOUND THEN
        RETURN QUERY SELECT NULL::UUID, 'invalid'::checkin_result, NULL::TEXT, NULL::ticket_class, NULL::TEXT, 0;
        RETURN;
    END IF;

    -- Check event match
    IF p_event_id IS NOT NULL AND v_inv.event_id != p_event_id THEN
        RETURN QUERY SELECT v_inv.id, 'wrong_event'::checkin_result, v_inv.guest_name, v_inv.ticket_class, v_inv.event_title, v_inv.checkin_count;
        RETURN;
    END IF;

    -- Check revoked
    IF v_inv.status = 'revoked' THEN
        RETURN QUERY SELECT v_inv.id, 'revoked'::checkin_result, v_inv.guest_name, v_inv.ticket_class, v_inv.event_title, v_inv.checkin_count;
        RETURN;
    END IF;

    -- Check expired
    IF v_inv.status = 'expired' OR (v_inv.expires_at IS NOT NULL AND v_inv.expires_at < now()) THEN
        RETURN QUERY SELECT v_inv.id, 'expired'::checkin_result, v_inv.guest_name, v_inv.ticket_class, v_inv.event_title, v_inv.checkin_count;
        RETURN;
    END IF;

    -- Check already checked in (atomic: the FOR UPDATE lock guarantees
    -- no other transaction can read stale checkin_count)
    IF v_inv.checkin_count > 0 AND NOT v_inv.allow_reentry THEN
        RETURN QUERY SELECT v_inv.id, 'already_checked_in'::checkin_result, v_inv.guest_name, v_inv.ticket_class, v_inv.event_title, v_inv.checkin_count;
        RETURN;
    END IF;

    -- Check gate class
    IF p_gate_id IS NOT NULL THEN
        IF NOT EXISTS (
            SELECT 1 FROM public.event_gates
            WHERE id = p_gate_id AND v_inv.ticket_class = ANY(allowed_classes)
        ) THEN
            RETURN QUERY SELECT v_inv.id, 'wrong_gate'::checkin_result, v_inv.guest_name, v_inv.ticket_class, v_inv.event_title, v_inv.checkin_count;
            RETURN;
        END IF;
    END IF;

    -- SUCCESS: atomically update the invitation within the same lock
    UPDATE public.invitations SET
        status = 'checked_in',
        checked_in_at = COALESCE(checked_in_at, now()),
        checkin_count = checkin_count + 1,
        updated_at = now()
    WHERE id = v_inv.id;

    RETURN QUERY SELECT v_inv.id, 'success'::checkin_result, v_inv.guest_name, v_inv.ticket_class, v_inv.event_title, v_inv.checkin_count + 1;
END;
$$;

-- ============================================================
-- 2) BATCH STATE MACHINE: valid transitions only
--    Prevents invalid status jumps (e.g. ready → generating)
-- ============================================================

CREATE OR REPLACE FUNCTION public.enforce_batch_transition()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    valid BOOLEAN := false;
BEGIN
    -- Allow any transition if old status is NULL (new row)
    IF OLD.status IS NULL THEN
        RETURN NEW;
    END IF;

    -- Define valid transitions
    CASE OLD.status
        WHEN 'draft' THEN
            valid := NEW.status IN ('queued', 'cancelled');
        WHEN 'queued' THEN
            valid := NEW.status IN ('generating_barcodes', 'cancelled', 'failed');
        WHEN 'generating_barcodes' THEN
            valid := NEW.status IN ('rendering_images', 'generating_pdf', 'cancelled', 'failed');
        WHEN 'rendering_images' THEN
            valid := NEW.status IN ('generating_pdf', 'cancelled', 'failed');
        WHEN 'generating_pdf' THEN
            valid := NEW.status IN ('generating_zip', 'cancelled', 'failed');
        WHEN 'generating_zip' THEN
            valid := NEW.status IN ('ready', 'cancelled', 'failed');
        WHEN 'ready' THEN
            valid := false;  -- terminal state
        WHEN 'failed' THEN
            valid := NEW.status IN ('queued');  -- retry requeues
        WHEN 'cancelled' THEN
            valid := false;  -- terminal state
        ELSE
            valid := false;
    END CASE;

    IF NOT valid THEN
        RAISE EXCEPTION 'Invalid batch status transition: % → %', OLD.status, NEW.status;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER enforce_batch_status_transition
    BEFORE UPDATE OF status ON public.generation_batches
    FOR EACH ROW
    EXECUTE FUNCTION public.enforce_batch_transition();

-- ============================================================
-- 3) BRUTE-FORCE PROTECTION: index for rate limiting lookups
-- ============================================================

-- Fast lookup for recent failed scan attempts by IP (for rate limiting)
CREATE INDEX IF NOT EXISTS idx_checkins_ip_recent
    ON public.checkins (ip_address, created_at DESC)
    WHERE result != 'success';

-- ============================================================
-- 4) BATCH METRICS: track timing and sizes
-- ============================================================

ALTER TABLE public.generation_batches
    ADD COLUMN IF NOT EXISTS started_at      TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS completed_at    TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS duration_ms     BIGINT,
    ADD COLUMN IF NOT EXISTS result_pdf_size BIGINT DEFAULT 0,
    ADD COLUMN IF NOT EXISTS result_zip_size BIGINT DEFAULT 0,
    ADD COLUMN IF NOT EXISTS error_summary   JSONB DEFAULT '{}';

-- ============================================================
-- 5) FONT ASSET REFERENCE: link elements to uploaded fonts
-- ============================================================

ALTER TABLE public.template_elements
    ADD COLUMN IF NOT EXISTS font_asset_id UUID REFERENCES public.template_assets(id) ON DELETE SET NULL;

-- ============================================================
-- DONE: Migration V5 complete
-- ============================================================


-- <<< END migration_v5_production_hardening.sql <<<

-- >>> BEGIN migration_v6_constraints_and_governance.sql >>>

-- ============================================================
-- Migration V6: Data Integrity Constraints & Governance
-- قيود سلامة البيانات وحوكمة النظام
-- ============================================================
-- 1) Template element coordinate constraints (0-1 range)
-- 2) Event quota constraints (>= 0)
-- 3) Batch progress constraint (0-100) — already exists via CHECK
-- 4) Result immutability: prevent modification of ready/cancelled batches
-- 5) Invitation snapshot policy enforcement
-- ============================================================

-- ============================================================
-- 1) TEMPLATE ELEMENT COORDINATES: must be 0.0 → 1.0
--    Relative coordinates allow resolution-independent layouts
-- ============================================================

ALTER TABLE public.template_elements
    ADD CONSTRAINT chk_element_x      CHECK (x >= 0 AND x <= 1),
    ADD CONSTRAINT chk_element_y      CHECK (y >= 0 AND y <= 1),
    ADD CONSTRAINT chk_element_width  CHECK (width >= 0 AND width <= 1),
    ADD CONSTRAINT chk_element_height CHECK (height >= 0 AND height <= 1);

-- ============================================================
-- 2) EVENT QUOTAS: must be >= 0 (0 = unlimited)
-- ============================================================

ALTER TABLE public.events
    ADD CONSTRAINT chk_vip_quota    CHECK (vip_quota >= 0),
    ADD CONSTRAINT chk_normal_quota CHECK (normal_quota >= 0);

-- ============================================================
-- 3) BATCH RESULT IMMUTABILITY
--    Once a batch is 'ready', its output URLs and metrics
--    cannot be modified. To regenerate, create a new batch.
-- ============================================================

CREATE OR REPLACE FUNCTION public.protect_ready_batch()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    -- Allow status changes (e.g. ready → ready is blocked by state machine anyway)
    -- But prevent modification of result data on terminal batches
    IF OLD.status IN ('ready', 'cancelled') THEN
        -- Only allow updating metadata (for admin notes)
        IF NEW.result_pdf_url IS DISTINCT FROM OLD.result_pdf_url
           OR NEW.result_zip_url IS DISTINCT FROM OLD.result_zip_url
           OR NEW.result_preview_urls IS DISTINCT FROM OLD.result_preview_urls
           OR NEW.count_done IS DISTINCT FROM OLD.count_done
           OR NEW.count_failed IS DISTINCT FROM OLD.count_failed
        THEN
            RAISE EXCEPTION 'Cannot modify results of a % batch. Create a new batch to regenerate.', OLD.status;
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER protect_ready_batch_results
    BEFORE UPDATE ON public.generation_batches
    FOR EACH ROW
    EXECUTE FUNCTION public.protect_ready_batch();

-- ============================================================
-- 4) STORAGE SIGNED URL POLICY
--    Add column to track when signed URLs were last refreshed
-- ============================================================

ALTER TABLE public.generation_batches
    ADD COLUMN IF NOT EXISTS urls_refreshed_at TIMESTAMPTZ;

-- ============================================================
-- 5) FONT ASSET GOVERNANCE
--    Restrict font assets to known safe MIME types
-- ============================================================

-- Only TTF/OTF allowed — Pillow/FreeType cannot render WOFF/WOFF2 at runtime.
ALTER TABLE public.template_assets
    ADD CONSTRAINT chk_font_mime CHECK (
        asset_type != 'font' OR mime_type IN (
            'font/ttf', 'font/otf',
            'application/x-font-ttf', 'application/x-font-otf',
            'application/octet-stream'
        )
    );

-- Font file size limit (5MB for fonts)
ALTER TABLE public.template_assets
    ADD CONSTRAINT chk_font_size CHECK (
        asset_type != 'font' OR file_size <= 5242880
    );

-- ============================================================
-- 6) INVITATION CHECKIN COUNT: must be >= 0
-- ============================================================

ALTER TABLE public.invitations
    ADD CONSTRAINT chk_checkin_count CHECK (checkin_count >= 0);

-- ============================================================
-- 7) OPTION B GUARDRAIL: prevent tenant_id mutation
--    Since service_role bypasses RLS, this trigger is the
--    last line of defense against accidental cross-tenant
--    data migration via UPDATE.
-- ============================================================

CREATE OR REPLACE FUNCTION public.prevent_tenant_id_change()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF OLD.tenant_id IS NOT NULL AND NEW.tenant_id IS DISTINCT FROM OLD.tenant_id THEN
        RAISE EXCEPTION 'Cannot change tenant_id (attempted: % → %)', OLD.tenant_id, NEW.tenant_id;
    END IF;
    RETURN NEW;
END;
$$;

-- Apply AUTOMATICALLY to every public table that has a tenant_id column.
-- This way, any future table with tenant_id is covered without manual updates.
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN
        SELECT table_schema, table_name
        FROM information_schema.columns
        WHERE column_name = 'tenant_id'
          AND table_schema = 'public'
    LOOP
        -- Drop if exists (idempotent re-run)
        EXECUTE format(
            'DROP TRIGGER IF EXISTS prevent_%I_tenant_change ON %I.%I;',
            r.table_name, r.table_schema, r.table_name
        );
        EXECUTE format(
            'CREATE TRIGGER prevent_%I_tenant_change
                BEFORE UPDATE ON %I.%I
                FOR EACH ROW
                EXECUTE FUNCTION public.prevent_tenant_id_change();',
            r.table_name, r.table_schema, r.table_name
        );
    END LOOP;
END;
$$;

-- ============================================================
-- DONE: Migration V6 complete
-- ============================================================


-- <<< END migration_v6_constraints_and_governance.sql <<<

-- >>> BEGIN migration_v7_platform_consistency.sql >>>

-- ============================================================
-- Migration V7: Platform Consistency Fixes
-- Ensures runtime behavior matches the invitations/check-in APIs.
-- ============================================================

-- Invalid scan attempts may not resolve to a known invitation yet.
ALTER TABLE public.checkins
    ALTER COLUMN invitation_id DROP NOT NULL;



-- <<< END migration_v7_platform_consistency.sql <<<
