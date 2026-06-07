-- ============================================================
-- Migration: إضافة حدود جديدة لكامل المنصة
-- guests_max, registration_forms_max, team_members_per_team
-- ============================================================

-- Free plan
INSERT INTO public.plan_limits (plan_id, key, value, period) VALUES
    ((SELECT id FROM plans WHERE code = 'free'), 'guests_max',                200,   'none'),
    ((SELECT id FROM plans WHERE code = 'free'), 'registration_forms_max',    1,     'none'),
    ((SELECT id FROM plans WHERE code = 'free'), 'team_members_per_team',     5,     'none')
ON CONFLICT (plan_id, key) DO NOTHING;

-- Pro plan
INSERT INTO public.plan_limits (plan_id, key, value, period) VALUES
    ((SELECT id FROM plans WHERE code = 'pro'), 'guests_max',                10000,  'none'),
    ((SELECT id FROM plans WHERE code = 'pro'), 'registration_forms_max',    -1,     'none'),
    ((SELECT id FROM plans WHERE code = 'pro'), 'team_members_per_team',     25,     'none')
ON CONFLICT (plan_id, key) DO NOTHING;

-- Enterprise plan (-1 = unlimited)
INSERT INTO public.plan_limits (plan_id, key, value, period) VALUES
    ((SELECT id FROM plans WHERE code = 'enterprise'), 'guests_max',              -1,   'none'),
    ((SELECT id FROM plans WHERE code = 'enterprise'), 'registration_forms_max',  -1,   'none'),
    ((SELECT id FROM plans WHERE code = 'enterprise'), 'team_members_per_team',   -1,   'none')
ON CONFLICT (plan_id, key) DO NOTHING;

-- Update plan feature descriptions
UPDATE public.plans SET features = '[
  "حدث واحد/شهر",
  "50 دعوة/حدث",
  "200 ضيف",
  "دعوات سريعة فقط",
  "بوابة واحدة",
  "فريق واحد (5 أعضاء)",
  "3 أعضاء مؤسسة",
  "نموذج تسجيل واحد"
]'::jsonb WHERE code = 'free';

UPDATE public.plans SET features = '[
  "20 حدث/شهر",
  "5,000 دعوة/حدث",
  "10,000 ضيف",
  "تصميم بإحداثيات",
  "5 بوابات",
  "5 فرق (25 عضو/فريق)",
  "25 عضو مؤسسة",
  "نماذج تسجيل غير محدودة",
  "RSVP",
  "تقارير متقدمة"
]'::jsonb WHERE code = 'pro';

UPDATE public.plans SET features = '[
  "أحداث غير محدودة",
  "دعوات غير محدودة",
  "ضيوف غير محدود",
  "تصميم بإحداثيات",
  "بوابات غير محدودة",
  "فرق غير محدودة",
  "أعضاء غير محدود",
  "نماذج تسجيل غير محدودة",
  "RSVP",
  "SSO",
  "SLA",
  "دعم مخصص 24/7"
]'::jsonb WHERE code = 'enterprise';
