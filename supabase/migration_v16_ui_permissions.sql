-- Migration v16: UI-level permission keys for granular button/tab control
BEGIN;

INSERT INTO public.permissions (key, description) VALUES
    ('ui.nav.dashboard', 'الوصول: لوحة التحكم الرئيسية'),
    ('ui.nav.users', 'الوصول: صفحة المستخدمين'),
    ('ui.nav.teams', 'الوصول: صفحة الفرق'),
    ('ui.nav.guests', 'الوصول: صفحة الضيوف'),
    ('ui.nav.events', 'الوصول: صفحة الأحداث'),
    ('ui.nav.invitations', 'الوصول: صفحة الدعوات'),
    ('ui.nav.checkin', 'الوصول: صفحة تسجيل الحضور'),
    ('ui.nav.settings', 'الوصول: صفحة الإعدادات'),
    ('ui.event.tab.analytics', 'الوصول: تبويب تحليلات الحدث'),
    ('ui.event.tab.settings', 'الوصول: تبويب إعدادات الحدث'),
    ('ui.event.tab.gates', 'الوصول: تبويب بوابات الدخول'),
    ('ui.event.tab.invitations', 'الوصول: تبويب إنشاء الدعوات'),
    ('ui.event.tab.rsvp', 'الوصول: تبويب تأكيد الحضور'),
    ('ui.event.tab.registration', 'الوصول: تبويب نموذج التسجيل'),
    ('ui.event.tab.templates', 'الوصول: تبويب قوالب الحفل'),
    ('ui.event.tab.barcodes', 'الوصول: تبويب سجلات التوليد'),
    ('ui.event.tab.final', 'الوصول: تبويب الدعوات النهائية'),
    ('ui.event.action.publish', 'العملية: نشر الحدث'),
    ('ui.event.action.delete', 'العملية: حذف الحدث'),
    ('ui.event.action.create', 'العملية: إنشاء حدث جديد'),
    ('ui.gates.action.create', 'العملية: إنشاء بوابة'),
    ('ui.gates.action.edit', 'العملية: تعديل بوابة'),
    ('ui.gates.action.delete', 'العملية: حذف بوابة'),
    ('ui.invitations.action.generate', 'العملية: توليد دعوات'),
    ('ui.invitations.action.send', 'العملية: إرسال دعوات'),
    ('ui.invitations.action.revoke', 'العملية: إلغاء دعوات'),
    ('ui.invitations.action.export', 'العملية: تصدير دعوات'),
    ('ui.rsvp.action.update', 'العملية: تحديث RSVP يدوياً'),
    ('ui.rsvp.action.export', 'العملية: تصدير RSVP'),
    ('ui.registration.action.manage', 'العملية: إدارة نموذج التسجيل'),
    ('ui.registration.action.approve', 'العملية: قبول/رفض متقدمين'),
    ('ui.templates.action.create', 'العملية: إنشاء قالب'),
    ('ui.templates.action.edit', 'العملية: تعديل قالب'),
    ('ui.templates.action.delete', 'العملية: حذف قالب'),
    ('ui.templates.action.design', 'العملية: فتح محرر التصميم'),
    ('ui.batches.action.delete', 'العملية: حذف دفعة توليد'),
    ('ui.batches.action.download', 'العملية: تحميل PDF/ZIP'),
    ('ui.guests.action.create', 'العملية: إضافة ضيف'),
    ('ui.guests.action.edit', 'العملية: تعديل ضيف'),
    ('ui.guests.action.delete', 'العملية: حذف ضيف'),
    ('ui.guests.action.import', 'العملية: استيراد ضيوف'),
    ('ui.teams.action.create', 'العملية: إنشاء فريق'),
    ('ui.teams.action.manage', 'العملية: إدارة أعضاء الفريق'),
    ('ui.teams.action.archive', 'العملية: أرشفة فريق'),
    ('ui.members.action.create', 'العملية: إضافة عضو'),
    ('ui.members.action.edit', 'العملية: تعديل عضو'),
    ('ui.members.action.delete', 'العملية: حذف عضو'),
    ('ui.checkin.action.scan', 'العملية: مسح QR'),
    ('ui.checkin.action.manual', 'العملية: تسجيل يدوي'),
    ('ui.settings.action.edit', 'العملية: تعديل إعدادات المؤسسة'),
    ('ui.roles.action.manage', 'العملية: إدارة الأدوار والصلاحيات')
ON CONFLICT (key) DO UPDATE SET description = EXCLUDED.description;

-- Grant all UI permissions to Admin role for existing tenants
INSERT INTO public.role_permissions (role_id, permission_key)
SELECT r.id, p.key
FROM public.roles r
CROSS JOIN public.permissions p
WHERE r.name = 'Admin' AND r.is_system_role = true AND p.key LIKE 'ui.%'
ON CONFLICT DO NOTHING;

-- Viewer: nav read-only + event tabs view
INSERT INTO public.role_permissions (role_id, permission_key)
SELECT r.id, p.key
FROM public.roles r
CROSS JOIN public.permissions p
WHERE r.name = 'Viewer' AND r.is_system_role = true
  AND p.key IN (
    'ui.nav.dashboard', 'ui.nav.events', 'ui.nav.invitations', 'ui.nav.checkin',
    'ui.event.tab.analytics', 'ui.event.tab.rsvp', 'ui.event.tab.final', 'ui.event.tab.barcodes'
  )
ON CONFLICT DO NOTHING;

-- Member: operational UI
INSERT INTO public.role_permissions (role_id, permission_key)
SELECT r.id, p.key
FROM public.roles r
CROSS JOIN public.permissions p
WHERE r.name = 'Member' AND r.is_system_role = true
  AND p.key LIKE 'ui.%'
  AND p.key NOT IN (
    'ui.event.action.delete', 'ui.gates.action.delete',
    'ui.invitations.action.revoke', 'ui.templates.action.delete',
    'ui.members.action.create', 'ui.members.action.edit', 'ui.members.action.delete',
    'ui.roles.action.manage', 'ui.teams.action.archive'
  )
ON CONFLICT DO NOTHING;

-- Designer: templates + events view
INSERT INTO public.role_permissions (role_id, permission_key)
SELECT r.id, p.key
FROM public.roles r
CROSS JOIN public.permissions p
WHERE r.name = 'Designer' AND r.is_system_role = true
  AND p.key IN (
    'ui.nav.dashboard', 'ui.nav.events',
    'ui.event.tab.analytics', 'ui.event.tab.templates', 'ui.event.tab.settings',
    'ui.templates.action.create', 'ui.templates.action.edit', 'ui.templates.action.design'
  )
ON CONFLICT DO NOTHING;

-- Check-in Staff
INSERT INTO public.role_permissions (role_id, permission_key)
SELECT r.id, p.key
FROM public.roles r
CROSS JOIN public.permissions p
WHERE r.name = 'Check-in Staff' AND r.is_system_role = true
  AND p.key IN (
    'ui.nav.dashboard', 'ui.nav.checkin', 'ui.nav.events',
    'ui.event.tab.analytics',
    'ui.checkin.action.scan', 'ui.checkin.action.manual'
  )
ON CONFLICT DO NOTHING;

COMMIT;
