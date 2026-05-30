-- ============================================================
-- SaaS Core Schema v2.0 (Core Only)
-- ============================================================
-- Core SaaS bootstrap only.
-- For the full invitations platform bootstrap, use:
--   supabase/schema_complete.sql
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
