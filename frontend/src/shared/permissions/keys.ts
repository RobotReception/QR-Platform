/**
 * All permission keys used for UI gating.
 * Each key maps to a backend permission in the `permissions` table.
 */
export const PERM = {
  // Navigation
  NAV_DASHBOARD: 'ui.nav.dashboard',
  NAV_USERS: 'ui.nav.users',
  NAV_TEAMS: 'ui.nav.teams',
  NAV_GUESTS: 'ui.nav.guests',
  NAV_EVENTS: 'ui.nav.events',
  NAV_INVITATIONS: 'ui.nav.invitations',
  NAV_CHECKIN: 'ui.nav.checkin',
  NAV_SETTINGS: 'ui.nav.settings',

  // Event tabs
  EVENT_TAB_ANALYTICS: 'ui.event.tab.analytics',
  EVENT_TAB_SETTINGS: 'ui.event.tab.settings',
  EVENT_TAB_GATES: 'ui.event.tab.gates',
  EVENT_TAB_INVITATIONS: 'ui.event.tab.invitations',
  EVENT_TAB_RSVP: 'ui.event.tab.rsvp',
  EVENT_TAB_REGISTRATION: 'ui.event.tab.registration',
  EVENT_TAB_TEMPLATES: 'ui.event.tab.templates',
  EVENT_TAB_BARCODES: 'ui.event.tab.barcodes',
  EVENT_TAB_FINAL: 'ui.event.tab.final',

  // Event actions
  EVENT_CREATE: 'ui.event.action.create',
  EVENT_PUBLISH: 'ui.event.action.publish',
  EVENT_DELETE: 'ui.event.action.delete',

  // Gates
  GATES_CREATE: 'ui.gates.action.create',
  GATES_EDIT: 'ui.gates.action.edit',
  GATES_DELETE: 'ui.gates.action.delete',

  // Invitations
  INV_GENERATE: 'ui.invitations.action.generate',
  INV_SEND: 'ui.invitations.action.send',
  INV_REVOKE: 'ui.invitations.action.revoke',
  INV_EXPORT: 'ui.invitations.action.export',

  // RSVP
  RSVP_UPDATE: 'ui.rsvp.action.update',
  RSVP_EXPORT: 'ui.rsvp.action.export',

  // Registration
  REG_MANAGE: 'ui.registration.action.manage',
  REG_APPROVE: 'ui.registration.action.approve',

  // Templates
  TMPL_CREATE: 'ui.templates.action.create',
  TMPL_EDIT: 'ui.templates.action.edit',
  TMPL_DELETE: 'ui.templates.action.delete',
  TMPL_DESIGN: 'ui.templates.action.design',

  // Batches
  BATCH_DELETE: 'ui.batches.action.delete',
  BATCH_DOWNLOAD: 'ui.batches.action.download',

  // Guests
  GUEST_CREATE: 'ui.guests.action.create',
  GUEST_EDIT: 'ui.guests.action.edit',
  GUEST_DELETE: 'ui.guests.action.delete',
  GUEST_IMPORT: 'ui.guests.action.import',

  // Teams
  TEAM_CREATE: 'ui.teams.action.create',
  TEAM_MANAGE: 'ui.teams.action.manage',
  TEAM_ARCHIVE: 'ui.teams.action.archive',

  // Members
  MEMBER_CREATE: 'ui.members.action.create',
  MEMBER_EDIT: 'ui.members.action.edit',
  MEMBER_DELETE: 'ui.members.action.delete',

  // Check-in
  CHECKIN_SCAN: 'ui.checkin.action.scan',
  CHECKIN_MANUAL: 'ui.checkin.action.manual',

  // Settings & roles
  SETTINGS_EDIT: 'ui.settings.action.edit',
  ROLES_MANAGE: 'ui.roles.action.manage',
} as const

export type PermissionKey = (typeof PERM)[keyof typeof PERM]

/** Grouped labels for the roles management UI (Arabic) */
export const PERMISSION_GROUPS: { label: string; keys: PermissionKey[] }[] = [
  {
    label: 'التنقل — القائمة الجانبية',
    keys: [
      PERM.NAV_DASHBOARD, PERM.NAV_USERS, PERM.NAV_TEAMS,
      PERM.NAV_EVENTS, PERM.NAV_SETTINGS,
    ],
  },
  {
    label: 'تبويبات تفاصيل الحدث',
    keys: [
      PERM.EVENT_TAB_ANALYTICS, PERM.EVENT_TAB_SETTINGS, PERM.EVENT_TAB_GATES,
      PERM.EVENT_TAB_INVITATIONS, PERM.EVENT_TAB_RSVP, PERM.EVENT_TAB_REGISTRATION,
      PERM.EVENT_TAB_TEMPLATES, PERM.EVENT_TAB_BARCODES, PERM.EVENT_TAB_FINAL,
    ],
  },
  {
    label: 'عمليات الحدث',
    keys: [PERM.EVENT_CREATE, PERM.EVENT_PUBLISH, PERM.EVENT_DELETE],
  },
  {
    label: 'البوابات',
    keys: [PERM.GATES_CREATE, PERM.GATES_EDIT, PERM.GATES_DELETE],
  },
  {
    label: 'الدعوات',
    keys: [PERM.INV_GENERATE, PERM.INV_SEND, PERM.INV_REVOKE, PERM.INV_EXPORT],
  },
  {
    label: 'RSVP والتسجيل',
    keys: [PERM.RSVP_UPDATE, PERM.RSVP_EXPORT, PERM.REG_MANAGE, PERM.REG_APPROVE],
  },
  {
    label: 'القوالب والتوليد',
    keys: [
      PERM.TMPL_CREATE, PERM.TMPL_EDIT, PERM.TMPL_DELETE, PERM.TMPL_DESIGN,
      PERM.BATCH_DELETE, PERM.BATCH_DOWNLOAD,
    ],
  },
  {
    label: 'الضيوف والفرق والأعضاء',
    keys: [
      PERM.GUEST_CREATE, PERM.GUEST_EDIT, PERM.GUEST_DELETE, PERM.GUEST_IMPORT,
      PERM.TEAM_CREATE, PERM.TEAM_MANAGE, PERM.TEAM_ARCHIVE,
      PERM.MEMBER_CREATE, PERM.MEMBER_EDIT, PERM.MEMBER_DELETE,
    ],
  },
  {
    label: 'تسجيل الحضور والإعدادات',
    keys: [PERM.CHECKIN_SCAN, PERM.CHECKIN_MANUAL, PERM.SETTINGS_EDIT, PERM.ROLES_MANAGE],
  },
]

export const PERMISSION_LABELS_AR: Record<string, string> = {
  [PERM.NAV_DASHBOARD]: 'الرئيسية',
  [PERM.NAV_USERS]: 'المستخدمون',
  [PERM.NAV_TEAMS]: 'الفرق',
  [PERM.NAV_GUESTS]: 'الضيوف',
  [PERM.NAV_EVENTS]: 'الأحداث',
  [PERM.NAV_INVITATIONS]: 'الدعوات',
  [PERM.NAV_CHECKIN]: 'تسجيل الحضور',
  [PERM.NAV_SETTINGS]: 'الإعدادات',
  [PERM.EVENT_TAB_ANALYTICS]: 'تبويب: تحليلات',
  [PERM.EVENT_TAB_SETTINGS]: 'تبويب: إعدادات',
  [PERM.EVENT_TAB_GATES]: 'تبويب: بوابات',
  [PERM.EVENT_TAB_INVITATIONS]: 'تبويب: إنشاء دعوات',
  [PERM.EVENT_TAB_RSVP]: 'تبويب: RSVP',
  [PERM.EVENT_TAB_REGISTRATION]: 'تبويب: التسجيل',
  [PERM.EVENT_TAB_TEMPLATES]: 'تبويب: قوالب',
  [PERM.EVENT_TAB_BARCODES]: 'تبويب: سجلات التوليد',
  [PERM.EVENT_TAB_FINAL]: 'تبويب: الدعوات النهائية',
  [PERM.EVENT_CREATE]: 'إنشاء حدث',
  [PERM.EVENT_PUBLISH]: 'نشر حدث',
  [PERM.EVENT_DELETE]: 'حذف حدث',
  [PERM.GATES_CREATE]: 'إنشاء بوابة',
  [PERM.GATES_EDIT]: 'تعديل بوابة',
  [PERM.GATES_DELETE]: 'حذف بوابة',
  [PERM.INV_GENERATE]: 'توليد دعوات',
  [PERM.INV_SEND]: 'إرسال دعوات',
  [PERM.INV_REVOKE]: 'إلغاء دعوات',
  [PERM.INV_EXPORT]: 'تصدير دعوات',
  [PERM.RSVP_UPDATE]: 'تحديث RSVP',
  [PERM.RSVP_EXPORT]: 'تصدير RSVP',
  [PERM.REG_MANAGE]: 'إدارة نموذج التسجيل',
  [PERM.REG_APPROVE]: 'قبول/رفض متقدمين',
  [PERM.TMPL_CREATE]: 'إنشاء قالب',
  [PERM.TMPL_EDIT]: 'تعديل قالب',
  [PERM.TMPL_DELETE]: 'حذف قالب',
  [PERM.TMPL_DESIGN]: 'محرر التصميم',
  [PERM.BATCH_DELETE]: 'حذف دفعة توليد',
  [PERM.BATCH_DOWNLOAD]: 'تحميل PDF/ZIP',
  [PERM.GUEST_CREATE]: 'إضافة ضيف',
  [PERM.GUEST_EDIT]: 'تعديل ضيف',
  [PERM.GUEST_DELETE]: 'حذف ضيف',
  [PERM.GUEST_IMPORT]: 'استيراد ضيوف',
  [PERM.TEAM_CREATE]: 'إنشاء فريق',
  [PERM.TEAM_MANAGE]: 'إدارة أعضاء الفريق',
  [PERM.TEAM_ARCHIVE]: 'أرشفة فريق',
  [PERM.MEMBER_CREATE]: 'إضافة عضو',
  [PERM.MEMBER_EDIT]: 'تعديل عضو',
  [PERM.MEMBER_DELETE]: 'حذف عضو',
  [PERM.CHECKIN_SCAN]: 'مسح QR',
  [PERM.CHECKIN_MANUAL]: 'تسجيل يدوي',
  [PERM.SETTINGS_EDIT]: 'تعديل إعدادات المؤسسة',
  [PERM.ROLES_MANAGE]: 'إدارة الأدوار',
}
