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
