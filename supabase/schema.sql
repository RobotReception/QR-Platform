-- ============================================================
-- SaaS Core Schema for Supabase
-- Tables: profiles, tenants, memberships, roles, permissions,
--         plans, plan_limits, subscriptions, subscription_events,
--         usage_counters, invites, tenant_settings, feature_flags,
--         audit_logs
-- ============================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- ENUMS
-- ============================================================

CREATE TYPE tenant_status AS ENUM ('active', 'suspended', 'deleted');
CREATE TYPE membership_status AS ENUM ('active', 'invited', 'disabled');
CREATE TYPE membership_role AS ENUM ('owner', 'admin', 'member', 'viewer');
CREATE TYPE subscription_status AS ENUM ('trialing', 'active', 'past_due', 'canceled', 'unpaid', 'incomplete');
CREATE TYPE invite_status AS ENUM ('pending', 'accepted', 'expired', 'revoked');
CREATE TYPE usage_period AS ENUM ('month', 'day', 'none');

-- ============================================================
-- 1) PROFILES
-- ============================================================

CREATE TABLE public.profiles (
    id          UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name   TEXT,
    avatar_url  TEXT,
    phone       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_profiles_created_at ON public.profiles(created_at);

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
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_tenants_slug ON public.tenants(slug);
CREATE INDEX idx_tenants_status ON public.tenants(status);
CREATE INDEX idx_tenants_created_by ON public.tenants(created_by);

-- ============================================================
-- 3) MEMBERSHIPS (users <-> tenants)
-- ============================================================

CREATE TABLE public.memberships (
    tenant_id   UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    role        membership_role NOT NULL DEFAULT 'member',
    status      membership_status NOT NULL DEFAULT 'active',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, user_id)
);

CREATE INDEX idx_memberships_user_id ON public.memberships(user_id);
CREATE INDEX idx_memberships_tenant_id ON public.memberships(tenant_id);
CREATE INDEX idx_memberships_role ON public.memberships(role);

-- ============================================================
-- 4) ROLES & PERMISSIONS (Advanced RBAC - optional)
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

CREATE TABLE public.permissions (
    key         TEXT PRIMARY KEY,  -- e.g. 'tickets.read', 'billing.manage'
    description TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE public.role_permissions (
    role_id         UUID NOT NULL REFERENCES public.roles(id) ON DELETE CASCADE,
    permission_key  TEXT NOT NULL REFERENCES public.permissions(key) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_key)
);

CREATE TABLE public.membership_roles (
    tenant_id   UUID NOT NULL,
    user_id     UUID NOT NULL,
    role_id     UUID NOT NULL REFERENCES public.roles(id) ON DELETE CASCADE,
    PRIMARY KEY (tenant_id, user_id, role_id),
    FOREIGN KEY (tenant_id, user_id) REFERENCES public.memberships(tenant_id, user_id) ON DELETE CASCADE
);

-- ============================================================
-- 5) PLANS (System-wide)
-- ============================================================

CREATE TABLE public.plans (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code            TEXT NOT NULL UNIQUE,  -- 'free', 'pro', 'enterprise'
    name            TEXT NOT NULL,
    price_monthly   NUMERIC(10, 2) NOT NULL DEFAULT 0,
    price_yearly    NUMERIC(10, 2),
    currency        TEXT NOT NULL DEFAULT 'USD',
    is_active       BOOLEAN NOT NULL DEFAULT true,
    sort_order      INT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- 6) PLAN LIMITS (Entitlements per plan)
-- ============================================================

CREATE TABLE public.plan_limits (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    plan_id     UUID NOT NULL REFERENCES public.plans(id) ON DELETE CASCADE,
    key         TEXT NOT NULL,  -- 'seats_max', 'messages_per_month', 'storage_mb', 'ai_requests_per_month'
    value       BIGINT NOT NULL,
    period      usage_period NOT NULL DEFAULT 'none',
    UNIQUE(plan_id, key)
);

CREATE INDEX idx_plan_limits_plan_id ON public.plan_limits(plan_id);

-- ============================================================
-- 7) SUBSCRIPTIONS (per tenant)
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
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_subscriptions_tenant_id ON public.subscriptions(tenant_id);
CREATE INDEX idx_subscriptions_status ON public.subscriptions(status);
CREATE INDEX idx_subscriptions_provider_sub_id ON public.subscriptions(provider_subscription_id);

-- ============================================================
-- 8) SUBSCRIPTION EVENTS (Audit trail for billing)
-- ============================================================

CREATE TABLE public.subscription_events (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    subscription_id     UUID NOT NULL REFERENCES public.subscriptions(id) ON DELETE CASCADE,
    event_type          TEXT NOT NULL,  -- 'invoice.paid', 'subscription.updated', etc.
    provider_event_id   TEXT,
    raw_payload         JSONB,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_sub_events_subscription_id ON public.subscription_events(subscription_id);
CREATE INDEX idx_sub_events_event_type ON public.subscription_events(event_type);

-- ============================================================
-- 9) USAGE COUNTERS
-- ============================================================

CREATE TABLE public.usage_counters (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    period_start    DATE NOT NULL,
    period_end      DATE NOT NULL,
    key             TEXT NOT NULL,  -- 'messages', 'ai_requests', 'storage_mb_used'
    value           BIGINT NOT NULL DEFAULT 0,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(tenant_id, period_start, key)
);

CREATE INDEX idx_usage_counters_tenant_period ON public.usage_counters(tenant_id, period_start);

-- Function to atomically increment usage
CREATE OR REPLACE FUNCTION public.increment_usage(
    p_tenant_id UUID,
    p_key TEXT,
    p_amount BIGINT DEFAULT 1
)
RETURNS BIGINT
LANGUAGE plpgsql
SECURITY DEFINER
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
-- 10) INVITES
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

-- ============================================================
-- 11) TENANT SETTINGS
-- ============================================================

CREATE TABLE public.tenant_settings (
    tenant_id   UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    key         TEXT NOT NULL,
    value       JSONB NOT NULL DEFAULT '{}',
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, key)
);

-- ============================================================
-- 12) FEATURE FLAGS
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
-- 13) AUDIT LOGS
-- ============================================================

CREATE TABLE public.audit_logs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID REFERENCES public.tenants(id) ON DELETE SET NULL,
    actor_user_id   UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    action          TEXT NOT NULL,  -- 'member.invite', 'subscription.upgrade', 'tenant.create'
    resource_type   TEXT,           -- 'tenant', 'membership', 'subscription'
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

-- ============================================================
-- 14) UPDATED_AT TRIGGER (reusable)
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

-- Apply to all tables with updated_at
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

CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.tenant_settings
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.feature_flags
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

-- ============================================================
-- 15) ROW LEVEL SECURITY (RLS)
-- ============================================================

-- Enable RLS on all tenant-scoped tables
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.role_permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.membership_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.usage_counters ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.invites ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tenant_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.feature_flags ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;

-- Helper function: get tenant IDs for current user
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

-- Helper function: check if user is member of tenant
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

-- Helper function: check if user has role in tenant
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

-- Helper function: check if user is owner or admin
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

-- ── Profiles ──
CREATE POLICY "Users can view own profile"
    ON public.profiles FOR SELECT
    USING (id = auth.uid());

CREATE POLICY "Users can update own profile"
    ON public.profiles FOR UPDATE
    USING (id = auth.uid());

-- Members can see profiles of people in same tenant
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

CREATE POLICY "Admins can manage roles"
    ON public.roles FOR ALL
    USING (public.is_admin_of(tenant_id));

-- ── Role Permissions ──
CREATE POLICY "Members can view role permissions"
    ON public.role_permissions FOR SELECT
    USING (
        role_id IN (
            SELECT r.id FROM public.roles r
            WHERE r.tenant_id IN (SELECT public.get_my_tenant_ids())
        )
    );

-- ── Membership Roles ──
CREATE POLICY "Members can view membership roles"
    ON public.membership_roles FOR SELECT
    USING (tenant_id IN (SELECT public.get_my_tenant_ids()));

-- ── Subscriptions ──
CREATE POLICY "Members can view their tenant subscriptions"
    ON public.subscriptions FOR SELECT
    USING (tenant_id IN (SELECT public.get_my_tenant_ids()));

-- ── Usage Counters ──
CREATE POLICY "Members can view their tenant usage"
    ON public.usage_counters FOR SELECT
    USING (tenant_id IN (SELECT public.get_my_tenant_ids()));

-- ── Invites ──
CREATE POLICY "Admins can view invites"
    ON public.invites FOR SELECT
    USING (tenant_id IN (SELECT public.get_my_tenant_ids()));

CREATE POLICY "Admins can create invites"
    ON public.invites FOR INSERT
    WITH CHECK (public.is_admin_of(tenant_id));

CREATE POLICY "Admins can update invites"
    ON public.invites FOR UPDATE
    USING (public.is_admin_of(tenant_id));

-- ── Tenant Settings ──
CREATE POLICY "Members can view tenant settings"
    ON public.tenant_settings FOR SELECT
    USING (tenant_id IN (SELECT public.get_my_tenant_ids()));

CREATE POLICY "Admins can manage tenant settings"
    ON public.tenant_settings FOR ALL
    USING (public.is_admin_of(tenant_id));

-- ── Feature Flags ──
CREATE POLICY "Members can view feature flags"
    ON public.feature_flags FOR SELECT
    USING (tenant_id IN (SELECT public.get_my_tenant_ids()));

-- ── Audit Logs ──
CREATE POLICY "Admins can view audit logs"
    ON public.audit_logs FOR SELECT
    USING (public.is_admin_of(tenant_id));

-- ============================================================
-- 16) SEED DATA: Default Plans
-- ============================================================

INSERT INTO public.plans (code, name, price_monthly, price_yearly, currency, sort_order) VALUES
    ('free',       'Free',       0,       0,       'USD', 1),
    ('pro',        'Pro',        29.00,   290.00,  'USD', 2),
    ('enterprise', 'Enterprise', 99.00,   990.00,  'USD', 3);

-- Free plan limits
INSERT INTO public.plan_limits (plan_id, key, value, period) VALUES
    ((SELECT id FROM public.plans WHERE code = 'free'), 'seats_max',             3,     'none'),
    ((SELECT id FROM public.plans WHERE code = 'free'), 'messages_per_month',    100,   'month'),
    ((SELECT id FROM public.plans WHERE code = 'free'), 'storage_mb',            500,   'none'),
    ((SELECT id FROM public.plans WHERE code = 'free'), 'ai_requests_per_month', 50,    'month');

-- Pro plan limits
INSERT INTO public.plan_limits (plan_id, key, value, period) VALUES
    ((SELECT id FROM public.plans WHERE code = 'pro'), 'seats_max',             25,     'none'),
    ((SELECT id FROM public.plans WHERE code = 'pro'), 'messages_per_month',    5000,   'month'),
    ((SELECT id FROM public.plans WHERE code = 'pro'), 'storage_mb',            10000,  'none'),
    ((SELECT id FROM public.plans WHERE code = 'pro'), 'ai_requests_per_month', 2000,   'month');

-- Enterprise plan limits
INSERT INTO public.plan_limits (plan_id, key, value, period) VALUES
    ((SELECT id FROM public.plans WHERE code = 'enterprise'), 'seats_max',             -1,      'none'),   -- unlimited
    ((SELECT id FROM public.plans WHERE code = 'enterprise'), 'messages_per_month',    -1,      'month'),  -- unlimited
    ((SELECT id FROM public.plans WHERE code = 'enterprise'), 'storage_mb',            100000,  'none'),
    ((SELECT id FROM public.plans WHERE code = 'enterprise'), 'ai_requests_per_month', -1,      'month');  -- unlimited
