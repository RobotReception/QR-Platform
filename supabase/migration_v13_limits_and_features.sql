-- ============================================================
-- Migration v13: ضبط حدود نماذج التسجيل وإلغاء تخصيصها
-- ============================================================

BEGIN;

-- 1. تحديث الحد الأقصى لنماذج التسجيل ليكون 1 لجميع الباقات في جدول حدود الباقات
UPDATE public.plan_limits
SET value = 1
WHERE key = 'registration_forms_max';

-- 2. تحديث قائمة المميزات المعروضة للباقات لتعكس هذا الحد (نموذج تسجيل واحد)
UPDATE public.plans
SET features = jsonb_set(
    features,
    '{}',
    (
        SELECT jsonb_agg(
            CASE 
                -- استبدال جملة "3 نماذج تسجيل" أو "نماذج تسجيل غير محدودة" بـ "نموذج تسجيل واحد"
                WHEN val.value::text LIKE '%نماذج تسجيل%' THEN '"نموذج تسجيل واحد"'::jsonb
                ELSE val.value
            END
        )
        FROM jsonb_array_elements(features) AS val
    )
)
WHERE code IN ('basic', 'pro', 'business', 'enterprise');

-- 3. إيقاف تنشيط إضافة نماذج التسجيل من لوحة تخصيص الباقات المخصصة
UPDATE public.plan_addons
SET is_active = false
WHERE key = 'registration_forms_max';

COMMIT;
