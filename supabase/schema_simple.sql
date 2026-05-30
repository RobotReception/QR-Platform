-- Simple Database Schema for QR Platform
-- Tables in dependency order (no circular references)

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Enums
CREATE TYPE tenant_status AS ENUM ('active', 'trial', 'suspended', 'cancelled', 'deleted');
CREATE TYPE membership_status AS ENUM ('active', 'invited', 'disabled');
CREATE TYPE membership_role AS ENUM ('owner', 'admin', 'member', 'viewer');
CREATE TYPE subscription_status AS ENUM ('trialing', 'active', 'past_due', 'canceled', 'unpaid', 'incomplete');

-- 1. PROFILES (no dependencies)
CREATE TABLE profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    full_name TEXT,
    avatar_url TEXT,
    phone TEXT,
    is_staff BOOLEAN DEFAULT false,
    status TEXT DEFAULT 'active',
    email_verified_at TIMESTAMPTZ,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 2. PLANS (no dependencies)
CREATE TABLE plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    description TEXT,
    price_monthly NUMERIC(10,2) DEFAULT 0,
    price_yearly NUMERIC(10,2) DEFAULT 0,
    max_users INTEGER DEFAULT 10,
    max_events INTEGER DEFAULT 100,
    max_invitations INTEGER DEFAULT 1000,
    features JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 3. TENANTS (depends on plans)
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    status tenant_status DEFAULT 'active',
    plan_id UUID REFERENCES plans(id),
    max_users INTEGER DEFAULT 10,
    max_events INTEGER DEFAULT 100,
    logo_url TEXT,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 4. MEMBERSHIPS (depends on tenants and profiles)
CREATE TABLE memberships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    profile_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    role membership_role DEFAULT 'member',
    status membership_status DEFAULT 'active',
    joined_at TIMESTAMPTZ DEFAULT now(),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(tenant_id, profile_id)
);

-- 5. SUBSCRIPTIONS (depends on tenants and plans)
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    plan_id UUID REFERENCES plans(id),
    status subscription_status DEFAULT 'trialing',
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 6. EVENTS (depends on tenants)
CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    event_date TIMESTAMPTZ NOT NULL,
    event_time TEXT,
    location TEXT,
    venue_name TEXT,
    max_guests INTEGER,
    image_url TEXT,
    status TEXT DEFAULT 'draft',
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 7. INVITATIONS (depends on events)
CREATE TABLE invitations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID REFERENCES events(id) ON DELETE CASCADE,
    guest_name TEXT NOT NULL,
    guest_count INT NOT NULL DEFAULT 1,
    guest_email TEXT,
    guest_phone TEXT,
    status TEXT DEFAULT 'pending',
    barcode TEXT UNIQUE,
    qr_code_url TEXT,
    check_in_at TIMESTAMPTZ,
    sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 8. GENERATION BATCHES (depends on events)
CREATE TABLE generation_batches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID REFERENCES events(id) ON DELETE CASCADE,
    total_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 9. INVITE TEMPLATES (depends on tenants)
CREATE TABLE invite_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    layout_config JSONB DEFAULT '{}',
    preview_image_url TEXT,
    is_default BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Function to update updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply triggers
CREATE TRIGGER trigger_profiles_updated_at BEFORE UPDATE ON profiles FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trigger_plans_updated_at BEFORE UPDATE ON plans FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trigger_tenants_updated_at BEFORE UPDATE ON tenants FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trigger_memberships_updated_at BEFORE UPDATE ON memberships FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trigger_subscriptions_updated_at BEFORE UPDATE ON subscriptions FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trigger_events_updated_at BEFORE UPDATE ON events FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trigger_invitations_updated_at BEFORE UPDATE ON invitations FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trigger_generation_batches_updated_at BEFORE UPDATE ON generation_batches FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trigger_invite_templates_updated_at BEFORE UPDATE ON invite_templates FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Seed data
INSERT INTO plans (name, slug, description, price_monthly, price_yearly, max_users, max_events, max_invitations) VALUES
('Free', 'free', 'Free plan for testing', 0, 0, 1, 5, 50),
('Pro', 'pro', 'Professional plan', 29.99, 299.99, 10, 100, 1000),
('Enterprise', 'enterprise', 'Enterprise plan', 99.99, 999.99, 100, 1000, 10000);

INSERT INTO profiles (email, full_name, is_staff, status) VALUES
('admin@qr.com', 'Admin User', true, 'active');

INSERT INTO tenants (name, slug, status, plan_id, max_users, max_events) 
SELECT 'Default Tenant', 'default-tenant', 'active', id, 10, 100 FROM plans WHERE slug = 'free';

INSERT INTO memberships (tenant_id, profile_id, role, status)
SELECT t.id, p.id, 'owner', 'active'
FROM tenants t, profiles p
WHERE t.slug = 'default-tenant' AND p.email = 'admin@qr.com';
