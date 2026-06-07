import { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Building2, CreditCard, Gauge, Loader2, Save, Settings, Sparkles } from 'lucide-react'
import { PERM, usePermission } from '@shared/permissions'
import { WorkspaceShell } from '@features/workspace/components/WorkspaceShell'
import { useAuthStore } from '@features/auth/store/authStore'
import { settingsAPI } from '../api/settingsApi'
import { subscriptionsAPI } from '../api/subscriptionsApi'
import { PricingModal } from '@features/dashboard/components/PricingModal'
import './settings.css'

const LIMIT_LABELS: Record<string, string> = {
  events_per_month: 'الفعاليات شهرياً',
  invitations_per_month: 'الدعوات شهرياً',
  invitations_per_event: 'الدعوات لكل حدث',
  gates_per_event: 'البوابات لكل حدث',
  teams_max: 'فرق العمل',
  seats_max: 'مقاعد لوحة التحكم',
  designed_templates: 'القوالب المصممة',
  guests_max: 'الضيوف',
  storage_mb: 'التخزين (MB)',
  messages_per_month: 'الرسائل شهرياً',
  ai_requests_per_month: 'طلبات الذكاء الاصطناعي',
}

function formatLimit(value: number) {
  return value === -1 ? 'غير محدود' : value.toLocaleString('ar-SA')
}

function formatDate(value?: string | null) {
  if (!value) return 'غير متوفر'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'غير متوفر'
  return new Intl.DateTimeFormat('ar-SA', { dateStyle: 'medium' }).format(date)
}

const USAGE_ORDER = [
  'events_per_month',
  'invitations_per_month',
  'invitations_per_event',
  'guests_max',
  'gates_per_event',
  'teams_max',
  'seats_max',
  'designed_templates',
  'storage_mb',
  'messages_per_month',
  'ai_requests_per_month',
] as const

export default function SettingsPage() {
  const tenantId = useAuthStore(s => s.currentTenantId)
  const tenants = useAuthStore(s => s.tenants)

  // Guard
  const hasAccess = usePermission(PERM.NAV_SETTINGS)
  if (!hasAccess) {
    return <Navigate to="/dashboard" replace />
  }
  const canEditSettings = usePermission(PERM.SETTINGS_EDIT)
  const queryClient = useQueryClient()
  const [name, setName] = useState('')
  const [msg, setMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [isPricingOpen, setIsPricingOpen] = useState(false)
  const currentMembership = tenants.find(t => t.tenant_id === tenantId)
  const canCancelSubscription = currentMembership?.role === 'owner'

  const { data: tenant, isLoading: tenantLoading } = useQuery({
    queryKey: ['settings-tenant', tenantId],
    queryFn: settingsAPI.getCurrentTenant,
    enabled: !!tenantId,
  })

  const { data: usage, isLoading: usageLoading } = useQuery({
    queryKey: ['settings-usage', tenantId],
    queryFn: settingsAPI.getUsage,
    enabled: !!tenantId,
  })

  const { data: subscription, isLoading: subscriptionLoading } = useQuery({
    queryKey: ['current-subscription', tenantId],
    queryFn: subscriptionsAPI.getCurrentSubscription,
    enabled: !!tenantId,
    retry: false,
  })

  const updateMutation = useMutation({
    mutationFn: (body: { name: string }) => settingsAPI.updateTenant(body),
    onSuccess: () => {
      setMsg({ type: 'success', text: 'تم حفظ الإعدادات بنجاح' })
      queryClient.invalidateQueries({ queryKey: ['settings-tenant', tenantId] })
    },
    onError: () => setMsg({ type: 'error', text: 'فشل حفظ الإعدادات' }),
  })

  const cancelMutation = useMutation({
    mutationFn: subscriptionsAPI.cancelSubscription,
    onSuccess: () => {
      setMsg({ type: 'success', text: 'تم جدولة إلغاء الاشتراك بنهاية الفترة الحالية' })
      queryClient.invalidateQueries({ queryKey: ['current-subscription', tenantId] })
      queryClient.invalidateQueries({ queryKey: ['dashboard', tenantId] })
    },
    onError: (err: any) => {
      setMsg({
        type: 'error',
        text: err?.response?.data?.detail || 'تعذر إلغاء الاشتراك حالياً. يرجى المحاولة لاحقاً.',
      })
    },
  })

  const displayName = name || tenant?.name || ''
  const usageLimits = (usage?.limits || [])
    .filter(l => LIMIT_LABELS[l.key])
    .filter((limit, index, arr) => arr.findIndex(item => item.key === limit.key) === index)
    .sort((a, b) => {
      const aIndex = USAGE_ORDER.indexOf(a.key as typeof USAGE_ORDER[number])
      const bIndex = USAGE_ORDER.indexOf(b.key as typeof USAGE_ORDER[number])
      const safeA = aIndex === -1 ? Number.MAX_SAFE_INTEGER : aIndex
      const safeB = bIndex === -1 ? Number.MAX_SAFE_INTEGER : bIndex
      return safeA - safeB
    })

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault()
    if (!displayName.trim()) return
    updateMutation.mutate({ name: displayName.trim() })
  }

  if (!tenantId) {
    return (
      <WorkspaceShell title="إعدادات المؤسسة" subtitle="إدارة بيانات المؤسسة والاشتراك">
        <div className="dash-state">يرجى اختيار مؤسسة أولاً</div>
      </WorkspaceShell>
    )
  }

  return (
    <WorkspaceShell
      title="إعدادات المؤسسة"
      subtitle="إدارة بيانات المؤسسة ومراقبة حدود الاستخدام"
    >
      <div className="settings-grid">
        <section className="settings-card">
          <h2><Building2 size={18} /> بيانات المؤسسة</h2>

          {msg && <div className={`settings-msg settings-msg--${msg.type}`}>{msg.text}</div>}

          {tenantLoading ? (
            <Loader2 size={24} className="spin" />
          ) : (
            <form onSubmit={handleSave}>
              <div className="settings-field">
                <label htmlFor="org-name">اسم المؤسسة</label>
                <input
                  id="org-name"
                  value={displayName}
                  onChange={e => { setName(e.target.value); setMsg(null) }}
                  placeholder="اسم المؤسسة"
                />
              </div>
              <div className="settings-field">
                <label htmlFor="org-slug">المعرّف (Slug)</label>
                <input id="org-slug" value={tenant?.slug || ''} disabled />
              </div>
              <div className="settings-field">
                <label htmlFor="org-status">الحالة</label>
                <input id="org-status" value={tenant?.status || ''} disabled />
              </div>
              {canEditSettings && (
                <div className="settings-actions">
                  <button type="submit" className="settings-btn" disabled={updateMutation.isPending}>
                    {updateMutation.isPending ? <Loader2 size={16} className="spin" /> : <Save size={16} />}
                    حفظ التغييرات
                  </button>
                </div>
              )}
            </form>
          )}
        </section>

        <section className="settings-card">
          <h2><CreditCard size={18} /> الفوترة والاشتراك</h2>

          {subscriptionLoading ? (
            <Loader2 size={24} className="spin" />
          ) : subscription ? (
            <div className="settings-subscription">
              <div className="settings-subscription__row">
                <span>الخطة الحالية</span>
                <strong>{subscription.plan_name}</strong>
              </div>
              <div className="settings-subscription__row">
                <span>الحالة</span>
                <strong>{subscription.status}</strong>
              </div>
              <div className="settings-subscription__row">
                <span>مزود الدفع</span>
                <strong>{subscription.provider}</strong>
              </div>
              <div className="settings-subscription__row">
                <span>السعر الحالي</span>
                <strong>
                  {(subscription.price_monthly ?? 0).toLocaleString('en-US')} {subscription.currency || 'USD'} / شهر
                </strong>
              </div>
              <div className="settings-subscription__row">
                <span>نهاية الفترة</span>
                <strong>{formatDate(subscription.current_period_end)}</strong>
              </div>
              <div className="settings-subscription__row">
                <span>الإلغاء بنهاية الفترة</span>
                <strong>{subscription.cancel_at_period_end ? 'نعم' : 'لا'}</strong>
              </div>

              <div className="settings-actions">
                <button type="button" className="settings-btn" onClick={() => setIsPricingOpen(true)}>
                  <Sparkles size={16} />
                  تغيير الباقة
                </button>
                {canCancelSubscription && !subscription.cancel_at_period_end && (
                  <button
                    type="button"
                    className="settings-btn settings-btn--danger"
                    disabled={cancelMutation.isPending}
                    onClick={() => {
                      if (window.confirm('سيتم إلغاء الاشتراك بنهاية الفترة الحالية. هل تريد المتابعة؟')) {
                        cancelMutation.mutate()
                      }
                    }}
                  >
                    {cancelMutation.isPending ? <Loader2 size={16} className="spin" /> : null}
                    إلغاء الاشتراك
                  </button>
                )}
              </div>
            </div>
          ) : (
            <div className="settings-subscription">
              <p style={{ color: 'var(--color-text-muted)', fontSize: 13, margin: 0 }}>
                لا يوجد اشتراك مدفوع نشط حالياً. يمكنك الترقية متى شئت من هنا.
              </p>
              <div className="settings-actions">
                <button type="button" className="settings-btn" onClick={() => setIsPricingOpen(true)}>
                  <Sparkles size={16} />
                  عرض الباقات
                </button>
              </div>
            </div>
          )}
        </section>

        <section className="settings-card">
          <h2><Gauge size={18} /> الاشتراك والاستخدام</h2>

          {usageLoading ? (
            <Loader2 size={24} className="spin" />
          ) : usage ? (
            <>
              <span className="settings-plan-badge">
                الباقة: {usage.plan_code}
              </span>
              <div className="settings-usage-list">
                {usageLimits.map(l => (
                    <div
                      key={l.key}
                      className={`settings-usage-item${l.is_exceeded ? ' settings-usage-item--exceeded' : ''}`}
                    >
                      <span>{LIMIT_LABELS[l.key]}</span>
                      <span>
                        {l.current_usage.toLocaleString('ar-SA')} / {formatLimit(l.limit)}
                      </span>
                    </div>
                  ))}
              </div>
            </>
          ) : (
            <p style={{ color: 'var(--color-text-muted)', fontSize: 13 }}>تعذّر تحميل بيانات الاستخدام</p>
          )}
        </section>

        <section className="settings-card">
          <h2><Settings size={18} /> تبديل المؤسسة</h2>
          <p style={{ fontSize: 13, color: 'var(--color-text-muted)', margin: '0 0 12px', lineHeight: 1.6 }}>
            يمكنك التبديل بين المؤسسات من القائمة الجانبية أعلى شريط التنقل.
            عند التبديل، تُحدَّث جميع البيانات تلقائياً وفق المؤسسة المختارة.
          </p>
        </section>
      </div>

      <PricingModal
        isOpen={isPricingOpen}
        onClose={() => setIsPricingOpen(false)}
        currentPlanCode={subscription?.plan_code || usage?.plan_code || tenant?.plan || 'starter'}
      />
    </WorkspaceShell>
  )
}
