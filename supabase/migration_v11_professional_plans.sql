-- ============================================================
-- Migration: نظام الباقات الاحترافي — 5 مستويات
-- Qentry Platform — Professional Plans System
-- ============================================================
-- هذا الملف يُعيد هيكلة الباقات بالكامل:
--   1. Starter  (مجانية)
--   2. Basic    (أساسية)
--   3. Pro      (احترافية)
--   4. Business (أعمال)
--   5. Enterprise (مؤسسات)
-- ============================================================

BEGIN;

-- ══════════════════════════════════════════════
-- 1. إضافة أعمدة جديدة لجدول plans إذا لم تكن موجودة
-- ══════════════════════════════════════════════
DO $$
BEGIN
    -- badge_color: لون شارة الباقة في الواجهة
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='plans' AND column_name='badge_color') THEN
        ALTER TABLE public.plans ADD COLUMN badge_color TEXT DEFAULT '#6b7280';
    END IF;
    -- subtitle: عنوان فرعي قصير
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='plans' AND column_name='subtitle') THEN
        ALTER TABLE public.plans ADD COLUMN subtitle TEXT DEFAULT '';
    END IF;
    -- is_popular: لتمييز الباقة الأكثر شعبية
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='plans' AND column_name='is_popular') THEN
        ALTER TABLE public.plans ADD COLUMN is_popular BOOLEAN DEFAULT false;
    END IF;
    -- price_yearly if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='plans' AND column_name='price_yearly') THEN
        ALTER TABLE public.plans ADD COLUMN price_yearly NUMERIC(10,2);
    END IF;
END $$;


-- ══════════════════════════════════════════════
-- 2. تحديث الباقات الحالية + إضافة الجديدة
-- ══════════════════════════════════════════════

-- ── 2a. تحديث Free → Starter ──
UPDATE public.plans SET
    name = 'Starter',
    code = 'starter',
    description = 'للتجربة والاستخدام الشخصي',
    subtitle = 'ابدأ مجاناً',
    price_monthly = 0,
    price_yearly = 0,
    currency = 'SAR',
    badge_color = '#6b7280',
    is_popular = false,
    sort_order = 1,
    features = '[
        "حدث واحد شهرياً",
        "50 دعوة لكل حدث",
        "200 ضيف كحد أقصى",
        "بوابة تسجيل واحدة",
        "فريق عمل واحد (5 أعضاء)",
        "3 مستخدمين للوحة التحكم",
        "قوالب جاهزة فقط",
        "نموذج تسجيل واحد",
        "500 MB تخزين",
        "تقارير أساسية",
        "دعم عبر البريد الإلكتروني"
    ]'::jsonb,
    updated_at = now()
WHERE code = 'free';

-- ── 2b. إضافة باقة Basic (أساسية) ──
INSERT INTO public.plans (code, name, description, subtitle, price_monthly, price_yearly, currency, badge_color, is_popular, sort_order, features)
VALUES (
    'basic',
    'Basic',
    'للأفراد ومنظمي الفعاليات الصغيرة',
    'الأكثر مرونة للبداية',
    200.00,
    1920.00,
    'SAR',
    '#3b82f6',
    false,
    2,
    '[
        "5 أحداث شهرياً",
        "500 دعوة لكل حدث",
        "2,000 ضيف كحد أقصى",
        "بوابتين لكل حدث",
        "فريقين (10 أعضاء/فريق)",
        "5 مستخدمين للوحة التحكم",
        "5 قوالب مصممة",
        "3 نماذج تسجيل",
        "2 GB تخزين",
        "1,000 دعوة شهرياً",
        "تقارير أساسية",
        "RSVP",
        "دعم عبر البريد الإلكتروني"
    ]'::jsonb
) ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    subtitle = EXCLUDED.subtitle,
    price_monthly = EXCLUDED.price_monthly,
    price_yearly = EXCLUDED.price_yearly,
    currency = EXCLUDED.currency,
    badge_color = EXCLUDED.badge_color,
    is_popular = EXCLUDED.is_popular,
    sort_order = EXCLUDED.sort_order,
    features = EXCLUDED.features,
    updated_at = now();

-- ── 2c. تحديث Pro (احترافية) ──
UPDATE public.plans SET
    name = 'Pro',
    description = 'للفرق المتوسطة ومنظمي الفعاليات المحترفين',
    subtitle = 'الأكثر شعبية',
    price_monthly = 500.00,
    price_yearly = 4800.00,
    currency = 'SAR',
    badge_color = '#8b5cf6',
    is_popular = true,
    sort_order = 3,
    features = '[
        "20 حدث شهرياً",
        "5,000 دعوة لكل حدث",
        "10,000 ضيف كحد أقصى",
        "5 بوابات لكل حدث",
        "5 فرق (25 عضو/فريق)",
        "25 مستخدم للوحة التحكم",
        "قوالب مصممة غير محدودة",
        "نماذج تسجيل غير محدودة",
        "10 GB تخزين",
        "10,000 دعوة شهرياً",
        "تقارير متقدمة وتحليلات",
        "RSVP مع تخصيصات",
        "تصدير PDF وExcel",
        "تصميم بإحداثيات متقدم",
        "دعم ذو أولوية"
    ]'::jsonb,
    updated_at = now()
WHERE code = 'pro';

-- ── 2d. إضافة باقة Business (أعمال) ──
INSERT INTO public.plans (code, name, description, subtitle, price_monthly, price_yearly, currency, badge_color, is_popular, sort_order, features)
VALUES (
    'business',
    'Business',
    'للشركات والمؤسسات متوسطة الحجم',
    'قوة بلا حدود',
    1200.00,
    11500.00,
    'SAR',
    '#f59e0b',
    false,
    4,
    '[
        "100 حدث شهرياً",
        "25,000 دعوة لكل حدث",
        "50,000 ضيف كحد أقصى",
        "15 بوابة لكل حدث",
        "15 فريق (50 عضو/فريق)",
        "100 مستخدم للوحة التحكم",
        "قوالب مصممة غير محدودة",
        "نماذج تسجيل غير محدودة",
        "50 GB تخزين",
        "50,000 دعوة شهرياً",
        "تقارير متقدمة + لوحة تحليلات",
        "RSVP مع تخصيصات",
        "تصدير PDF وExcel",
        "تصميم بإحداثيات متقدم",
        "API Access",
        "Webhook Notifications",
        "مدير حساب مخصص",
        "دعم هاتفي + بريد + واتساب"
    ]'::jsonb
) ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    subtitle = EXCLUDED.subtitle,
    price_monthly = EXCLUDED.price_monthly,
    price_yearly = EXCLUDED.price_yearly,
    currency = EXCLUDED.currency,
    badge_color = EXCLUDED.badge_color,
    is_popular = EXCLUDED.is_popular,
    sort_order = EXCLUDED.sort_order,
    features = EXCLUDED.features,
    updated_at = now();

-- ── 2e. تحديث Enterprise (مؤسسات) ──
UPDATE public.plans SET
    name = 'Enterprise',
    description = 'للمؤسسات الكبرى والجهات الحكومية',
    subtitle = 'حلول مخصصة بالكامل',
    price_monthly = 0,
    price_yearly = 0,
    currency = 'SAR',
    badge_color = '#059669',
    is_popular = false,
    sort_order = 5,
    features = '[
        "أحداث غير محدودة",
        "دعوات غير محدودة",
        "ضيوف غير محدود",
        "بوابات غير محدودة",
        "فرق غير محدودة",
        "مستخدمين غير محدود",
        "قوالب مصممة غير محدودة",
        "نماذج تسجيل غير محدودة",
        "200 GB تخزين (قابل للزيادة)",
        "تقارير متقدمة + لوحة تحليلات مخصصة",
        "RSVP + تخصيص كامل",
        "API Access + Webhooks",
        "SSO (تسجيل دخول موحد)",
        "SLA (اتفاقية مستوى خدمة)",
        "White Label (علامة تجارية مخصصة)",
        "On-premise أو Cloud مخصص",
        "مدير حساب مخصص VIP",
        "دعم مخصص 24/7 بكل القنوات",
        "تدريب فريق العمل"
    ]'::jsonb,
    updated_at = now()
WHERE code = 'enterprise';


-- ══════════════════════════════════════════════
-- 3. تحديث existing subscriptions من free إلى starter
-- ══════════════════════════════════════════════
-- تحديث tenants table
UPDATE public.tenants SET plan = 'starter' WHERE plan = 'free';


-- ══════════════════════════════════════════════
-- 4. حذف الحدود القديمة وإعادة إنشائها بالكامل
-- ══════════════════════════════════════════════

-- حذف حدود الباقات الحالية لإعادة بنائها
DELETE FROM public.plan_limits
WHERE plan_id IN (SELECT id FROM plans WHERE code IN ('starter', 'free', 'basic', 'pro', 'business', 'enterprise'));


-- ── 4a. Starter (المجانية) ──
INSERT INTO public.plan_limits (plan_id, key, value, period) VALUES
    ((SELECT id FROM plans WHERE code = 'starter'), 'seats_max',                3,      'none'),
    ((SELECT id FROM plans WHERE code = 'starter'), 'events_per_month',         1,      'month'),
    ((SELECT id FROM plans WHERE code = 'starter'), 'invitations_per_event',    50,     'none'),
    ((SELECT id FROM plans WHERE code = 'starter'), 'invitations_per_month',    50,     'month'),
    ((SELECT id FROM plans WHERE code = 'starter'), 'teams_max',                1,      'none'),
    ((SELECT id FROM plans WHERE code = 'starter'), 'team_members_per_team',    5,      'none'),
    ((SELECT id FROM plans WHERE code = 'starter'), 'designed_templates',       0,      'none'),
    ((SELECT id FROM plans WHERE code = 'starter'), 'gates_per_event',          1,      'none'),
    ((SELECT id FROM plans WHERE code = 'starter'), 'guests_max',               200,    'none'),
    ((SELECT id FROM plans WHERE code = 'starter'), 'registration_forms_max',   1,      'none'),
    ((SELECT id FROM plans WHERE code = 'starter'), 'storage_mb',               500,    'none'),
    ((SELECT id FROM plans WHERE code = 'starter'), 'messages_per_month',       100,    'month'),
    ((SELECT id FROM plans WHERE code = 'starter'), 'ai_requests_per_month',    20,     'month')
ON CONFLICT (plan_id, key) DO UPDATE SET value = EXCLUDED.value, period = EXCLUDED.period;


-- ── 4b. Basic (الأساسية) ──
INSERT INTO public.plan_limits (plan_id, key, value, period) VALUES
    ((SELECT id FROM plans WHERE code = 'basic'), 'seats_max',                5,      'none'),
    ((SELECT id FROM plans WHERE code = 'basic'), 'events_per_month',         5,      'month'),
    ((SELECT id FROM plans WHERE code = 'basic'), 'invitations_per_event',    500,    'none'),
    ((SELECT id FROM plans WHERE code = 'basic'), 'invitations_per_month',    1000,   'month'),
    ((SELECT id FROM plans WHERE code = 'basic'), 'teams_max',                2,      'none'),
    ((SELECT id FROM plans WHERE code = 'basic'), 'team_members_per_team',    10,     'none'),
    ((SELECT id FROM plans WHERE code = 'basic'), 'designed_templates',       5,      'none'),
    ((SELECT id FROM plans WHERE code = 'basic'), 'gates_per_event',          2,      'none'),
    ((SELECT id FROM plans WHERE code = 'basic'), 'guests_max',               2000,   'none'),
    ((SELECT id FROM plans WHERE code = 'basic'), 'registration_forms_max',   3,      'none'),
    ((SELECT id FROM plans WHERE code = 'basic'), 'storage_mb',               2000,   'none'),
    ((SELECT id FROM plans WHERE code = 'basic'), 'messages_per_month',       500,    'month'),
    ((SELECT id FROM plans WHERE code = 'basic'), 'ai_requests_per_month',    100,    'month')
ON CONFLICT (plan_id, key) DO UPDATE SET value = EXCLUDED.value, period = EXCLUDED.period;


-- ── 4c. Pro (الاحترافية) ──
INSERT INTO public.plan_limits (plan_id, key, value, period) VALUES
    ((SELECT id FROM plans WHERE code = 'pro'), 'seats_max',                25,     'none'),
    ((SELECT id FROM plans WHERE code = 'pro'), 'events_per_month',         20,     'month'),
    ((SELECT id FROM plans WHERE code = 'pro'), 'invitations_per_event',    5000,   'none'),
    ((SELECT id FROM plans WHERE code = 'pro'), 'invitations_per_month',    10000,  'month'),
    ((SELECT id FROM plans WHERE code = 'pro'), 'teams_max',                5,      'none'),
    ((SELECT id FROM plans WHERE code = 'pro'), 'team_members_per_team',    25,     'none'),
    ((SELECT id FROM plans WHERE code = 'pro'), 'designed_templates',       -1,     'none'),
    ((SELECT id FROM plans WHERE code = 'pro'), 'gates_per_event',          5,      'none'),
    ((SELECT id FROM plans WHERE code = 'pro'), 'guests_max',               10000,  'none'),
    ((SELECT id FROM plans WHERE code = 'pro'), 'registration_forms_max',   -1,     'none'),
    ((SELECT id FROM plans WHERE code = 'pro'), 'storage_mb',               10000,  'none'),
    ((SELECT id FROM plans WHERE code = 'pro'), 'messages_per_month',       5000,   'month'),
    ((SELECT id FROM plans WHERE code = 'pro'), 'ai_requests_per_month',    2000,   'month')
ON CONFLICT (plan_id, key) DO UPDATE SET value = EXCLUDED.value, period = EXCLUDED.period;


-- ── 4d. Business (أعمال) ──
INSERT INTO public.plan_limits (plan_id, key, value, period) VALUES
    ((SELECT id FROM plans WHERE code = 'business'), 'seats_max',                100,    'none'),
    ((SELECT id FROM plans WHERE code = 'business'), 'events_per_month',         100,    'month'),
    ((SELECT id FROM plans WHERE code = 'business'), 'invitations_per_event',    25000,  'none'),
    ((SELECT id FROM plans WHERE code = 'business'), 'invitations_per_month',    50000,  'month'),
    ((SELECT id FROM plans WHERE code = 'business'), 'teams_max',                15,     'none'),
    ((SELECT id FROM plans WHERE code = 'business'), 'team_members_per_team',    50,     'none'),
    ((SELECT id FROM plans WHERE code = 'business'), 'designed_templates',       -1,     'none'),
    ((SELECT id FROM plans WHERE code = 'business'), 'gates_per_event',          15,     'none'),
    ((SELECT id FROM plans WHERE code = 'business'), 'guests_max',               50000,  'none'),
    ((SELECT id FROM plans WHERE code = 'business'), 'registration_forms_max',   -1,     'none'),
    ((SELECT id FROM plans WHERE code = 'business'), 'storage_mb',               50000,  'none'),
    ((SELECT id FROM plans WHERE code = 'business'), 'messages_per_month',       -1,     'month'),
    ((SELECT id FROM plans WHERE code = 'business'), 'ai_requests_per_month',    10000,  'month')
ON CONFLICT (plan_id, key) DO UPDATE SET value = EXCLUDED.value, period = EXCLUDED.period;


-- ── 4e. Enterprise (المؤسسات) ──
INSERT INTO public.plan_limits (plan_id, key, value, period) VALUES
    ((SELECT id FROM plans WHERE code = 'enterprise'), 'seats_max',                -1,     'none'),
    ((SELECT id FROM plans WHERE code = 'enterprise'), 'events_per_month',         -1,     'month'),
    ((SELECT id FROM plans WHERE code = 'enterprise'), 'invitations_per_event',    -1,     'none'),
    ((SELECT id FROM plans WHERE code = 'enterprise'), 'invitations_per_month',    -1,     'month'),
    ((SELECT id FROM plans WHERE code = 'enterprise'), 'teams_max',                -1,     'none'),
    ((SELECT id FROM plans WHERE code = 'enterprise'), 'team_members_per_team',    -1,     'none'),
    ((SELECT id FROM plans WHERE code = 'enterprise'), 'designed_templates',       -1,     'none'),
    ((SELECT id FROM plans WHERE code = 'enterprise'), 'gates_per_event',          -1,     'none'),
    ((SELECT id FROM plans WHERE code = 'enterprise'), 'guests_max',               -1,     'none'),
    ((SELECT id FROM plans WHERE code = 'enterprise'), 'registration_forms_max',   -1,     'none'),
    ((SELECT id FROM plans WHERE code = 'enterprise'), 'storage_mb',               200000, 'none'),
    ((SELECT id FROM plans WHERE code = 'enterprise'), 'messages_per_month',       -1,     'month'),
    ((SELECT id FROM plans WHERE code = 'enterprise'), 'ai_requests_per_month',    -1,     'month')
ON CONFLICT (plan_id, key) DO UPDATE SET value = EXCLUDED.value, period = EXCLUDED.period;


-- ══════════════════════════════════════════════
-- 5. تحديث الاشتراكات الحالية للباقات القديمة
-- ══════════════════════════════════════════════
-- ربط الاشتراكات القديمة بالباقة الجديدة starter
UPDATE public.subscriptions
SET plan_id = (SELECT id FROM plans WHERE code = 'starter')
WHERE plan_id = (SELECT id FROM plans WHERE code = 'free')
  AND status IN ('active', 'trialing');

COMMIT;
