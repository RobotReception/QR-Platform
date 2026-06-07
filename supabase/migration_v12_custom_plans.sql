-- ============================================================
-- Migration v12: نظام تخصيص الباقات — Custom Plan Builder
-- يتيح للمستخدم اختيار أي باقة أساسية ثم إضافة موارد إضافية
-- ============================================================

BEGIN;

-- ══════════════════════════════════════════════
-- 1. جدول العناصر الإضافية مع أسعارها
-- ══════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS public.plan_addons (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key             TEXT NOT NULL UNIQUE,
    label_ar        TEXT NOT NULL,
    label_en        TEXT NOT NULL,
    unit_ar         TEXT NOT NULL DEFAULT '',
    unit_en         TEXT NOT NULL DEFAULT '',
    icon            TEXT DEFAULT '📦',
    min_value       INT NOT NULL DEFAULT 0,
    max_value       INT NOT NULL DEFAULT -1,
    step            INT NOT NULL DEFAULT 1,
    price_per_unit  NUMERIC(8,2) NOT NULL,
    category        TEXT NOT NULL DEFAULT 'general',
    sort_order      INT NOT NULL DEFAULT 0,
    is_active       BOOLEAN DEFAULT true,
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- ══════════════════════════════════════════════
-- 2. جدول الباقات المخصصة
-- ══════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS public.custom_plans (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    base_plan_id        UUID REFERENCES public.plans(id),
    name                TEXT NOT NULL DEFAULT 'باقتي المخصصة',
    addons              JSONB NOT NULL DEFAULT '{}',
    base_price          NUMERIC(10,2) NOT NULL DEFAULT 0,
    addons_price        NUMERIC(10,2) NOT NULL DEFAULT 0,
    total_price_monthly NUMERIC(10,2) NOT NULL DEFAULT 0,
    total_price_yearly  NUMERIC(10,2) NOT NULL DEFAULT 0,
    final_limits        JSONB NOT NULL DEFAULT '{}',
    status              TEXT NOT NULL DEFAULT 'draft',
    created_by          UUID,
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_custom_plans_tenant ON public.custom_plans(tenant_id);
CREATE INDEX IF NOT EXISTS idx_custom_plans_status ON public.custom_plans(status);

-- ══════════════════════════════════════════════
-- 3. بذر بيانات العناصر الإضافية (تسعير احترافي)
-- ══════════════════════════════════════════════
-- التسعير مبني على:
--   - أسعار تنافسية لسوق الخليج
--   - تسعير بالحزم (كل 100 دعوة مثلاً) لسهولة الحساب
--   - خصومات ضمنية عند الشراء بكميات كبيرة

INSERT INTO public.plan_addons (key, label_ar, label_en, unit_ar, unit_en, icon, min_value, max_value, step, price_per_unit, category, sort_order) VALUES
    -- ── أحداث ──
    ('events_per_month',       'أحداث شهرية',           'Monthly Events',         'حدث',     'event',      '📅', 1,    500,   1,    15.00, 'events',      1),

    -- ── دعوات وباركود ──
    ('invitations_per_event',  'دعوات لكل حدث',         'Invitations per Event',  'دعوة',    'invitation', '✉️', 100,  100000, 100, 5.00,  'invitations', 2),
    ('invitations_per_month',  'دعوات شهرية',           'Monthly Invitations',    'دعوة',    'invitation', '📨', 100,  200000, 100, 3.00,  'invitations', 3),

    -- ── بوابات (مسح QR) ──
    ('gates_per_event',        'بوابات لكل حدث',        'Gates per Event',        'بوابة',   'gate',       '🚪', 1,    100,   1,    10.00, 'events',      4),

    -- ── ضيوف ──
    ('guests_max',             'سعة الضيوف القصوى',     'Max Guests',             'ضيف',    'guest',      '👥', 100,  200000, 100, 4.00,  'guests',      5),

    -- ── فرق العمل ──
    ('teams_max',              'فرق العمل',             'Teams',                  'فريق',   'team',       '👔', 1,    100,   1,    20.00, 'teams',       6),
    ('team_members_per_team',  'أعضاء لكل فريق',       'Members per Team',       'عضو',    'member',     '👤', 5,    200,   5,    5.00,  'teams',       7),

    -- ── مستخدمو النظام ──
    ('seats_max',              'مستخدمو لوحة التحكم',   'Dashboard Users',        'مستخدم', 'user',       '🖥️', 1,    500,   1,    25.00, 'users',       8),

    -- ── قوالب وتصاميم ──
    ('designed_templates',     'قوالب مصممة',           'Designed Templates',     'قالب',   'template',   '🎨', 1,    200,   1,    10.00, 'templates',   9),
    ('registration_forms_max', 'نماذج التسجيل',         'Registration Forms',     'نموذج',  'form',       '📋', 1,    100,   1,    15.00, 'forms',       10),

    -- ── تخزين ──
    ('storage_mb',             'مساحة التخزين',         'Storage',                'GB',     'GB',         '💾', 1,    1000,  1,    5.00,  'storage',     11),

    -- ── رسائل و AI ──
    ('messages_per_month',     'رسائل شهرية',           'Monthly Messages',       'رسالة',  'message',    '💬', 100,  100000, 100, 3.00,  'messaging',   12),
    ('ai_requests_per_month',  'طلبات AI شهرية',        'Monthly AI Requests',    'طلب',    'request',    '🤖', 100,  100000, 100, 8.00,  'ai',          13)

ON CONFLICT (key) DO UPDATE SET
    label_ar = EXCLUDED.label_ar,
    label_en = EXCLUDED.label_en,
    unit_ar = EXCLUDED.unit_ar,
    unit_en = EXCLUDED.unit_en,
    icon = EXCLUDED.icon,
    min_value = EXCLUDED.min_value,
    max_value = EXCLUDED.max_value,
    step = EXCLUDED.step,
    price_per_unit = EXCLUDED.price_per_unit,
    category = EXCLUDED.category,
    sort_order = EXCLUDED.sort_order;

-- ══════════════════════════════════════════════
-- 4. إضافة العمود is_customizable لجدول plans
-- ══════════════════════════════════════════════
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='plans' AND column_name='is_customizable') THEN
        ALTER TABLE public.plans ADD COLUMN is_customizable BOOLEAN DEFAULT true;
    END IF;
END $$;

-- جميع الباقات قابلة للتخصيص
UPDATE public.plans SET is_customizable = true;

-- ══════════════════════════════════════════════
-- 5. RLS (Row Level Security) على custom_plans
-- ══════════════════════════════════════════════
ALTER TABLE public.plan_addons ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.custom_plans ENABLE ROW LEVEL SECURITY;

-- plan_addons: قراءة عامة
DROP POLICY IF EXISTS "plan_addons_public_read" ON public.plan_addons;
CREATE POLICY "plan_addons_public_read" ON public.plan_addons FOR SELECT USING (true);

-- custom_plans: القراءة والكتابة مرتبطة بالمستأجر
DROP POLICY IF EXISTS "custom_plans_tenant_access" ON public.custom_plans;
CREATE POLICY "custom_plans_tenant_access" ON public.custom_plans
    FOR ALL USING (tenant_id IN (
        SELECT m.tenant_id FROM memberships m WHERE m.user_id = auth.uid() AND m.status = 'active'
    ));

COMMIT;
