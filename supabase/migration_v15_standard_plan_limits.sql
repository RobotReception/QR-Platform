-- ============================================================
-- Migration v15: تحديث حدود وأوصاف الباقات الأساسية لمنصة Qentry
-- ============================================================

BEGIN;

-- ── 1. تحديث أوصاف وأسعار الباقات في جدول plans ──

UPDATE public.plans
SET price_monthly = 0.00,
    price_yearly = 0.00,
    description = 'التجربة الشخصية والفعاليات التجريبية الصغيرة',
    features = '[
      "100 دعوة شهرياً",
      "إرسال عبر الإيميل فقط",
      "دعوات RSVP متوفرة",
      "تنزيل التقارير غير مدعوم",
      "تصميم بالذكاء الاصطناعي غير مدعوم"
    ]'::jsonb
WHERE code = 'starter';

UPDATE public.plans
SET price_monthly = 200.00,
    price_yearly = 1920.00,
    description = 'الأفراد ومنظمي الفعاليات المحدودة',
    features = '[
      "1,500 دعوة شهرياً",
      "إرسال عبر الإيميل فقط",
      "دعوات RSVP متوفرة",
      "تنزيل التقارير بصيغة HTML فقط",
      "تصميم بالذكاء الاصطناعي غير مدعوم"
    ]'::jsonb
WHERE code = 'basic';

UPDATE public.plans
SET price_monthly = 500.00,
    price_yearly = 4800.00,
    description = 'الشركات المتوسطة ومنظمي الفعاليات المحترفين',
    features = '[
      "10,000 دعوة شهرياً",
      "إرسال مزدوج (إيميل + واتساب)",
      "دعوات RSVP تفاعلية كاملة",
      "تنزيل التقارير (Excel + HTML)",
      "تصميم القوالب بالذكاء الاصطناعي"
    ]'::jsonb
WHERE code = 'pro';

UPDATE public.plans
SET price_monthly = 1200.00,
    price_yearly = 11500.00,
    description = 'الشركات الكبرى والمؤتمرات الضخمة',
    features = '[
      "75,000 دعوة شهرياً",
      "إرسال مزدوج وسريع (إيميل + واتساب)",
      "دعوات RSVP مع تذكير تلقائي ذكي",
      "تنزيل التقارير (Excel + HTML) مع فلاتر مخصصة",
      "تصميم القوالب بالذكاء الاصطناعي بالكامل"
    ]'::jsonb
WHERE code = 'business';

UPDATE public.plans
SET price_monthly = 0.00,
    price_yearly = 0.00,
    description = 'الجهات الحكومية والمؤسسات الكبرى',
    features = '[
      "حدود وموارد غير محدودة بالكامل",
      "بوابة واتساب مخصصة برقم خاص",
      "ربط مباشر بالأنظمة الداخلية API",
      " White Label (علامة تجارية مخصصة)",
      "دعم مخصص 24/7 بكل القنوات"
    ]'::jsonb
WHERE code = 'enterprise';


-- ── 2. تحديث وإدخال حدود الباقات المحدثة في plan_limits ──

-- Starter
INSERT INTO public.plan_limits (plan_id, key, value, period) VALUES
    ((SELECT id FROM plans WHERE code = 'starter'), 'events_per_month',         1,    'month'),
    ((SELECT id FROM plans WHERE code = 'starter'), 'invitations_per_month',    100,  'month'),
    ((SELECT id FROM plans WHERE code = 'starter'), 'gates_per_event',          1,    'none'),
    ((SELECT id FROM plans WHERE code = 'starter'), 'teams_max',                1,    'none'),
    ((SELECT id FROM plans WHERE code = 'starter'), 'seats_max',                2,    'none'),
    ((SELECT id FROM plans WHERE code = 'starter'), 'designed_templates',       1,    'none')
ON CONFLICT (plan_id, key) DO UPDATE SET value = EXCLUDED.value;

-- Basic
INSERT INTO public.plan_limits (plan_id, key, value, period) VALUES
    ((SELECT id FROM plans WHERE code = 'basic'), 'events_per_month',         3,    'month'),
    ((SELECT id FROM plans WHERE code = 'basic'), 'invitations_per_month',    1500, 'month'),
    ((SELECT id FROM plans WHERE code = 'basic'), 'gates_per_event',          2,    'none'),
    ((SELECT id FROM plans WHERE code = 'basic'), 'teams_max',                2,    'none'),
    ((SELECT id FROM plans WHERE code = 'basic'), 'seats_max',                5,    'none'),
    ((SELECT id FROM plans WHERE code = 'basic'), 'designed_templates',       3,    'none')
ON CONFLICT (plan_id, key) DO UPDATE SET value = EXCLUDED.value;

-- Pro
INSERT INTO public.plan_limits (plan_id, key, value, period) VALUES
    ((SELECT id FROM plans WHERE code = 'pro'), 'events_per_month',         10,    'month'),
    ((SELECT id FROM plans WHERE code = 'pro'), 'invitations_per_month',    10000, 'month'),
    ((SELECT id FROM plans WHERE code = 'pro'), 'gates_per_event',          5,     'none'),
    ((SELECT id FROM plans WHERE code = 'pro'), 'teams_max',                5,     'none'),
    ((SELECT id FROM plans WHERE code = 'pro'), 'seats_max',                20,    'none'),
    ((SELECT id FROM plans WHERE code = 'pro'), 'designed_templates',       10,    'none')
ON CONFLICT (plan_id, key) DO UPDATE SET value = EXCLUDED.value;

-- Business
INSERT INTO public.plan_limits (plan_id, key, value, period) VALUES
    ((SELECT id FROM plans WHERE code = 'business'), 'events_per_month',         50,    'month'),
    ((SELECT id FROM plans WHERE code = 'business'), 'invitations_per_month',    75000, 'month'),
    ((SELECT id FROM plans WHERE code = 'business'), 'gates_per_event',          15,    'none'),
    ((SELECT id FROM plans WHERE code = 'business'), 'teams_max',                15,    'none'),
    ((SELECT id FROM plans WHERE code = 'business'), 'seats_max',                75,    'none'),
    ((SELECT id FROM plans WHERE code = 'business'), 'designed_templates',       30,    'none')
ON CONFLICT (plan_id, key) DO UPDATE SET value = EXCLUDED.value;

-- Enterprise
INSERT INTO public.plan_limits (plan_id, key, value, period) VALUES
    ((SELECT id FROM plans WHERE code = 'enterprise'), 'events_per_month',         -1,    'month'),
    ((SELECT id FROM plans WHERE code = 'enterprise'), 'invitations_per_month',    -1,  'month'),
    ((SELECT id FROM plans WHERE code = 'enterprise'), 'gates_per_event',          -1,    'none'),
    ((SELECT id FROM plans WHERE code = 'enterprise'), 'teams_max',                -1,    'none'),
    ((SELECT id FROM plans WHERE code = 'enterprise'), 'seats_max',                -1,    'none'),
    ((SELECT id FROM plans WHERE code = 'enterprise'), 'designed_templates',       -1,    'none')
ON CONFLICT (plan_id, key) DO UPDATE SET value = EXCLUDED.value;

COMMIT;
