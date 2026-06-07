-- ============================================================
-- Migration v14: تحديث أسعار وخطوات الإضافات للباقات المخصصة
-- ============================================================

BEGIN;

-- 1. إيقاف تنشيط جميع الإضافات بشكل افتراضي لتصفية القائمة
UPDATE public.plan_addons
SET is_active = false;

-- 2. تحديث وتنشيط الإضافات الستة المحددة بدقة في الطلب الجديد
-- أحداث شهرية (events_per_month): الخطوة 1، السعر 20
UPDATE public.plan_addons
SET is_active = true,
    step = 1,
    price_per_unit = 20.00
WHERE key = 'events_per_month';

-- دعوات شهرية (invitations_per_month): الخطوة 500، السعر 15
UPDATE public.plan_addons
SET is_active = true,
    step = 500,
    price_per_unit = 15.00
WHERE key = 'invitations_per_month';

-- بوابات لكل حدث (gates_per_event): الخطوة 1، السعر 10
UPDATE public.plan_addons
SET is_active = true,
    step = 1,
    price_per_unit = 10.00
WHERE key = 'gates_per_event';

-- فرق العمل (teams_max): الخطوة 1، السعر 15
UPDATE public.plan_addons
SET is_active = true,
    step = 1,
    price_per_unit = 15.00
WHERE key = 'teams_max';

-- مستخدمو لوحة التحكم (seats_max): الخطوة 1، السعر 25
UPDATE public.plan_addons
SET is_active = true,
    step = 1,
    price_per_unit = 25.00
WHERE key = 'seats_max';

-- قوالب مصممة (designed_templates): الخطوة 1، السعر 10
UPDATE public.plan_addons
SET is_active = true,
    step = 1,
    price_per_unit = 10.00
WHERE key = 'designed_templates';

COMMIT;
