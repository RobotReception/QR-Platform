import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import {
  BarChart3, Building2, Users, CreditCard, FileText, Shield,
  TrendingUp, DollarSign, UserPlus, Calendar, Globe,
  Search, Ban, CheckCircle2, XCircle,
  RefreshCcw, Crown, Zap,
  Package, Settings2, LogOut,
} from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { platformAPI } from '../api/platformApi'
import { PlatformRolesTab } from '../components/PlatformRolesTab'
import type {
  PlatformAnalytics, PlanOverviewItem, AddonItem
} from '../api/platformApi'
import { useAuthStore } from '@features/auth/store/authStore'
import './platform.css'

/* ── Number formatter ── */
const nf = new Intl.NumberFormat('ar-SA')
const cf = new Intl.NumberFormat('ar-SA', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
function n(v?: number | null) { return nf.format(v || 0) }
function currency(v?: number | null) { return `${cf.format(v || 0)} ر.س` }

/* ── Tab definitions ── */
type TabKey = 'overview' | 'tenants' | 'users' | 'roles' | 'plans' | 'subscriptions' | 'audit'

const TABS: { key: TabKey; label: string; icon: typeof BarChart3 }[] = [
  { key: 'overview',      label: 'نظرة عامة',  icon: BarChart3 },
  { key: 'tenants',       label: 'المؤسسات',   icon: Building2 },
  { key: 'users',         label: 'المستخدمين', icon: Users },
  { key: 'roles',         label: 'الأدوار',    icon: Shield },
  { key: 'plans',         label: 'الباقات',    icon: Package },
  { key: 'subscriptions', label: 'الاشتراكات', icon: CreditCard },
  { key: 'audit',         label: 'السجلات',    icon: FileText },
]

const STATUS_COLORS: Record<string, string> = {
  active: '#22c55e', trial: '#3b82f6', suspended: '#f59e0b', cancelled: '#ef4444', deleted: '#6b7280',
}

const STATUS_LABELS: Record<string, string> = {
  active: 'نشط', trial: 'تجريبي', suspended: 'معلّق', cancelled: 'ملغى',
}

/* ══════════════════════════════════════════════════
   KPI Card
   ══════════════════════════════════════════════════ */
function KpiCard({ title, value, subtitle, icon: Icon, color, delay = 0 }: {
  title: string; value: string; subtitle?: string; icon: typeof TrendingUp; color: string; delay?: number
}) {
  return (
    <motion.div
      className="plat-kpi"
      initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay }}
    >
      <div className="plat-kpi__icon" style={{ background: `${color}18`, color }}><Icon size={20} /></div>
      <div className="plat-kpi__body">
        <span className="plat-kpi__title">{title}</span>
        <strong className="plat-kpi__value">{value}</strong>
        {subtitle && <span className="plat-kpi__sub">{subtitle}</span>}
      </div>
    </motion.div>
  )
}

/* ══════════════════════════════════════════════════
   Mini Bar Chart (plan distribution)
   ══════════════════════════════════════════════════ */
function PlanDistChart({ data }: { data: PlatformAnalytics['plan_distribution'] }) {
  const max = Math.max(...data.map(d => d.count), 1)
  return (
    <div className="plat-plan-chart">
      {data.map((d) => (
        <div key={d.plan} className="plat-plan-chart__bar-group">
          <div className="plat-plan-chart__bar-wrap">
            <motion.div
              className="plat-plan-chart__bar"
              style={{ background: d.badge_color || '#6b7280' }}
              initial={{ height: 0 }} animate={{ height: `${Math.max((d.count / max) * 100, 4)}%` }}
              transition={{ duration: 0.6, delay: 0.2 }}
            />
          </div>
          <span className="plat-plan-chart__label">{d.plan_name}</span>
          <span className="plat-plan-chart__count">{d.count}</span>
        </div>
      ))}
    </div>
  )
}

/* ══════════════════════════════════════════════════
   Trend Sparkline
   ══════════════════════════════════════════════════ */
function TrendSparkline({ data, color = '#C9A96E' }: { data: { date: string; value: number }[]; color?: string }) {
  if (!data.length) return null
  const max = Math.max(...data.map(d => d.value), 1)
  const w = 300; const h = 60; const pad = 4
  const points = data.map((d, i) => ({
    x: pad + (i / Math.max(data.length - 1, 1)) * (w - pad * 2),
    y: h - pad - (d.value / max) * (h - pad * 2)
  }))
  const pathD = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' ')
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="plat-sparkline" preserveAspectRatio="none">
      <defs><linearGradient id="sg" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor={color} stopOpacity="0.3" />
        <stop offset="100%" stopColor={color} stopOpacity="0" />
      </linearGradient></defs>
      <path d={`${pathD} L${points[points.length - 1]!.x},${h} L${points[0].x},${h} Z`} fill="url(#sg)" />
      <path d={pathD} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

/* ══════════════════════════════════════════════════
   STATUS BADGE
   ══════════════════════════════════════════════════ */
function StatusBadge({ status }: { status: string }) {
  return (
    <span className="plat-badge" style={{
      background: `${STATUS_COLORS[status] || '#6b7280'}20`,
      color: STATUS_COLORS[status] || '#6b7280',
      borderColor: `${STATUS_COLORS[status] || '#6b7280'}40`,
    }}>
      {STATUS_LABELS[status] || status}
    </span>
  )
}

/* ══════════════════════════════════════════════════
   TAB: OVERVIEW
   ══════════════════════════════════════════════════ */
function OverviewTab({ data }: { data: PlatformAnalytics }) {
  const k = data.kpis; const r = data.revenue
  return (
    <div className="plat-overview">
      {/* KPIs Row */}
      <div className="plat-kpis-grid">
        <KpiCard title="المؤسسات" value={n(k.total_tenants)} subtitle={`${n(k.new_tenants_30d)} جديد (30 يوم)`} icon={Building2} color="#8b5cf6" delay={0} />
        <KpiCard title="المستخدمين" value={n(k.total_users)} subtitle={`${n(k.new_users_30d)} جديد (30 يوم)`} icon={Users} color="#3b82f6" delay={0.05} />
        <KpiCard title="الإيرادات الشهرية" value={currency(r.mrr)} subtitle={`${n(r.paying_tenants)} مشترك مدفوع`} icon={DollarSign} color="#22c55e" delay={0.1} />
        <KpiCard title="الإيرادات السنوية" value={currency(r.arr)} subtitle={`متوسط ${currency(r.avg_revenue_per_tenant)}/مؤسسة`} icon={TrendingUp} color="#C9A96E" delay={0.15} />
        <KpiCard title="الاشتراكات النشطة" value={n(k.active_subscriptions)} subtitle={`${n(k.trial_tenants)} تجريبي`} icon={CreditCard} color="#f59e0b" delay={0.2} />
        <KpiCard title="الأحداث" value={n(k.total_events)} subtitle={`${n(k.total_invitations)} دعوة`} icon={Calendar} color="#ec4899" delay={0.25} />
      </div>

      {/* Charts Row */}
      <div className="plat-charts-grid">
        {/* Plan Distribution */}
        <motion.div className="plat-panel" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
          <div className="plat-panel__head"><Package size={18} /><h3>توزيع الباقات</h3></div>
          <PlanDistChart data={data.plan_distribution} />
        </motion.div>

        {/* Trend */}
        <motion.div className="plat-panel" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.35 }}>
          <div className="plat-panel__head"><TrendingUp size={18} /><h3>اتجاه النمو (30 يوم)</h3></div>
          <div className="plat-trend-legends">
            <span><span className="plat-dot" style={{ background: '#8b5cf6' }} />مؤسسات</span>
            <span><span className="plat-dot" style={{ background: '#3b82f6' }} />مستخدمين</span>
          </div>
          <TrendSparkline data={data.trend_30d.map(t => ({ date: t.date, value: t.new_tenants }))} color="#8b5cf6" />
          <TrendSparkline data={data.trend_30d.map(t => ({ date: t.date, value: t.new_users }))} color="#3b82f6" />
        </motion.div>

        {/* Status Distribution */}
        <motion.div className="plat-panel" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}>
          <div className="plat-panel__head"><Shield size={18} /><h3>حالات المؤسسات</h3></div>
          <div className="plat-status-list">
            {data.status_distribution.map(s => (
              <div key={s.status} className="plat-status-row">
                <StatusBadge status={s.status} />
                <strong>{n(s.count)}</strong>
              </div>
            ))}
          </div>
        </motion.div>
      </div>

      {/* Recent & Top */}
      <div className="plat-dual-grid">
        <motion.div className="plat-panel" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.45 }}>
          <div className="plat-panel__head"><UserPlus size={18} /><h3>آخر المؤسسات المسجلة</h3></div>
          <table className="plat-table"><thead><tr><th>الاسم</th><th>الباقة</th><th>الحالة</th><th>الأعضاء</th></tr></thead>
            <tbody>{data.recent_tenants.map(t => (
              <tr key={t.id}><td>{t.name}</td><td><span className="plat-plan-tag">{t.plan}</span></td><td><StatusBadge status={t.status} /></td><td>{t.members_count}</td></tr>
            ))}</tbody>
          </table>
        </motion.div>

        <motion.div className="plat-panel" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}>
          <div className="plat-panel__head"><Zap size={18} /><h3>الأكثر نشاطاً</h3></div>
          <table className="plat-table"><thead><tr><th>الاسم</th><th>الأحداث</th><th>الدعوات</th><th>الأعضاء</th></tr></thead>
            <tbody>{data.top_tenants.map(t => (
              <tr key={t.id}><td>{t.name}</td><td>{n(t.events_count)}</td><td>{n(t.invitations_count)}</td><td>{n(t.members_count)}</td></tr>
            ))}</tbody>
          </table>
        </motion.div>
      </div>
    </div>
  )
}

/* ══════════════════════════════════════════════════
   TAB: TENANTS
   ══════════════════════════════════════════════════ */
function TenantsTab() {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const qc = useQueryClient()

  const { data: tenants = [], isLoading } = useQuery({
    queryKey: ['platform-tenants', search, statusFilter],
    queryFn: () => platformAPI.listTenants({ search: search || undefined, status: statusFilter || undefined, limit: 100 }),
  })

  const suspendMut = useMutation({ mutationFn: platformAPI.suspendTenant, onSuccess: () => qc.invalidateQueries({ queryKey: ['platform-tenants'] }) })
  const activateMut = useMutation({ mutationFn: platformAPI.activateTenant, onSuccess: () => qc.invalidateQueries({ queryKey: ['platform-tenants'] }) })
  const cancelMut = useMutation({ mutationFn: platformAPI.cancelTenant, onSuccess: () => qc.invalidateQueries({ queryKey: ['platform-tenants'] }) })

  return (
    <div className="plat-tab-content">
      <div className="plat-toolbar">
        <div className="plat-search-wrap"><Search size={16} /><input placeholder="بحث بالاسم أو المعرّف..." value={search} onChange={e => setSearch(e.target.value)} /></div>
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
          <option value="">كل الحالات</option>
          <option value="active">نشط</option>
          <option value="trial">تجريبي</option>
          <option value="suspended">معلّق</option>
          <option value="cancelled">ملغى</option>
        </select>
      </div>
      {isLoading ? <div className="plat-loading">جار التحميل...</div> : (
        <table className="plat-table plat-table--full">
          <thead><tr><th>المؤسسة</th><th>المعرّف</th><th>الباقة</th><th>الحالة</th><th>الأعضاء</th><th>التاريخ</th><th>إجراءات</th></tr></thead>
          <tbody>
            {tenants.map(t => (
              <tr key={t.id}>
                <td><strong>{t.name}</strong></td>
                <td className="plat-mono">{t.slug}</td>
                <td><span className="plat-plan-tag">{t.plan}</span></td>
                <td><StatusBadge status={t.status} /></td>
                <td>{t.members_count}</td>
                <td className="plat-date">{new Date(t.created_at).toLocaleDateString('ar-SA')}</td>
                <td className="plat-actions">
                  {t.status === 'active' && (
                    <button className="plat-act-btn plat-act-btn--warn" onClick={() => suspendMut.mutate(t.id)} title="تعليق"><Ban size={14} /></button>
                  )}
                  {(t.status === 'suspended' || t.status === 'cancelled') && (
                    <button className="plat-act-btn plat-act-btn--ok" onClick={() => activateMut.mutate(t.id)} title="تفعيل"><CheckCircle2 size={14} /></button>
                  )}
                  {t.status !== 'cancelled' && (
                    <button className="plat-act-btn plat-act-btn--danger" onClick={() => cancelMut.mutate(t.id)} title="إلغاء"><XCircle size={14} /></button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

/* ══════════════════════════════════════════════════
   TAB: USERS
   ══════════════════════════════════════════════════ */
function UsersTab() {
  const [search, setSearch] = useState('')
  const { data, isLoading } = useQuery({
    queryKey: ['platform-users', search],
    queryFn: () => platformAPI.listUsers({ search: search || undefined, limit: 100 }),
  })

  return (
    <div className="plat-tab-content">
      <div className="plat-toolbar">
        <div className="plat-search-wrap"><Search size={16} /><input placeholder="بحث بالاسم أو البريد..." value={search} onChange={e => setSearch(e.target.value)} /></div>
        <span className="plat-count">{n(data?.total)} مستخدم</span>
      </div>
      {isLoading ? <div className="plat-loading">جار التحميل...</div> : (
        <table className="plat-table plat-table--full">
          <thead><tr><th>المستخدم</th><th>البريد الإلكتروني</th><th>المؤسسات</th><th>الصلاحية</th><th>التسجيل</th><th>آخر دخول</th></tr></thead>
          <tbody>
            {data?.users.map(u => (
              <tr key={u.id}>
                <td className="plat-user-cell">
                  <div className="plat-avatar">{u.avatar_url ? <img src={u.avatar_url} alt="" /> : <span>{(u.full_name || '?')[0]}</span>}</div>
                  <strong>{u.full_name || 'بدون اسم'}</strong>
                </td>
                <td className="plat-mono">{u.email}</td>
                <td>{u.tenants_count}</td>
                <td>{u.is_staff ? <span className="plat-badge plat-badge--staff"><Crown size={12} />مشرف</span> : <span className="plat-badge">مستخدم</span>}</td>
                <td className="plat-date">{new Date(u.created_at).toLocaleDateString('ar-SA')}</td>
                <td className="plat-date">{u.last_login_at ? new Date(u.last_login_at).toLocaleDateString('ar-SA') : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

/* ══════════════════════════════════════════════════
   TAB: PLANS
   ══════════════════════════════════════════════════ */
const LIMIT_LABELS: Record<string, string> = {
  seats_max: 'الحد الأقصى للمستخدمين',
  events_per_month: 'الأحداث شهرياً',
  invitations_per_event: 'الدعوات لكل حدث',
  invitations_per_month: 'الدعوات شهرياً',
  teams_max: 'فرق العمل',
  team_members_per_team: 'أعضاء الفريق',
  designed_templates: 'القوالب المصممة',
  gates_per_event: 'البوابات لكل حدث',
  guests_max: 'سعة الضيوف القصوى',
  registration_forms_max: 'نماذج التسجيل',
  storage_mb: 'مساحة التخزين (MB)',
  messages_per_month: 'الرسائل شهرياً',
  ai_requests_per_month: 'طلبات AI شهرياً',
}

function PlansTab() {
  const qc = useQueryClient()
  const { data, isLoading } = useQuery({ queryKey: ['platform-plans'], queryFn: platformAPI.plansOverview })

  /* ── Editor States ── */
  const [editingPlan, setEditingPlan] = useState<PlanOverviewItem | null>(null)
  const [planLimits, setPlanLimits] = useState<{ key: string; value: number; period: string }[]>([])
  const [loadingLimits, setLoadingLimits] = useState(false)
  const [savingPlan, setSavingPlan] = useState(false)

  const [editingAddon, setEditingAddon] = useState<AddonItem | null>(null)
  const [savingAddon, setSavingAddon] = useState(false)

  /* ── Plan Form States ── */
  const [planForm, setPlanForm] = useState({
    name: '',
    subtitle: '',
    description: '',
    price_monthly: 0,
    price_yearly: 0,
    badge_color: '',
    is_popular: false,
    is_active: true,
  })

  /* ── Addon Form States ── */
  const [addonForm, setAddonForm] = useState({
    label_ar: '',
    label_en: '',
    unit_ar: '',
    icon: '',
    price_per_unit: 0,
  })

  /* ── Actions ── */
  const handleEditPlan = async (plan: PlanOverviewItem) => {
    setEditingPlan(plan)
    setPlanForm({
      name: plan.name,
      subtitle: plan.subtitle || '',
      description: plan.description || '',
      price_monthly: plan.price_monthly,
      price_yearly: plan.price_yearly,
      badge_color: plan.badge_color || '#6b7280',
      is_popular: plan.is_popular,
      is_active: plan.is_active,
    })
    setLoadingLimits(true)
    setPlanLimits([])
    try {
      const limits = await platformAPI.getPlanLimits(plan.id)
      setPlanLimits(limits)
    } catch (err) {
      console.error('Failed to get plan limits', err)
    } finally {
      setLoadingLimits(false)
    }
  }

  const handleLimitChange = (key: string, val: number) => {
    setPlanLimits(prev => prev.map(l => l.key === key ? { ...l, value: val } : l))
  }

  const handleSavePlan = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!editingPlan) return
    setSavingPlan(true)
    try {
      // 1. Update general plan info
      await platformAPI.updatePlan(editingPlan.id, planForm)
      // 2. Update limits
      await platformAPI.updatePlanLimits(editingPlan.id, planLimits)
      
      qc.invalidateQueries({ queryKey: ['platform-plans'] })
      setEditingPlan(null)
      alert('تم تحديث الباقة بنجاح')
    } catch (err) {
      console.error('Failed to save plan details', err)
      alert('فشل في حفظ التعديلات')
    } finally {
      setSavingPlan(false)
    }
  }

  const handleEditAddon = (addon: AddonItem) => {
    setEditingAddon(addon)
    setAddonForm({
      label_ar: addon.label_ar,
      label_en: addon.label_en,
      unit_ar: addon.unit_ar || '',
      icon: addon.icon || '📦',
      price_per_unit: addon.price_per_unit,
    })
  }

  const handleSaveAddon = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!editingAddon) return
    setSavingAddon(true)
    try {
      await platformAPI.updateAddon(editingAddon.id, addonForm)
      qc.invalidateQueries({ queryKey: ['platform-plans'] })
      setEditingAddon(null)
      alert('تم تحديث سعر الإضافة بنجاح')
    } catch (err) {
      console.error('Failed to save addon details', err)
      alert('فشل في حفظ تعديلات الإضافة')
    } finally {
      setSavingAddon(false)
    }
  }

  if (isLoading) return <div className="plat-loading">جار التحميل...</div>
  if (!data) return null

  return (
    <div className="plat-tab-content">
      {/* Plans grid */}
      <div className="plat-plans-grid">
        {data.plans.map(p => (
          <motion.div key={p.id} className="plat-plan-card" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.3 }}>
            <div className="plat-plan-card__head" style={{ borderColor: p.badge_color }}>
              <span className="plat-plan-card__badge" style={{ background: p.badge_color }}>{p.name}</span>
              {p.is_popular && <Crown size={14} className="plat-plan-card__pop" />}
            </div>
            <div className="plat-plan-card__price">
              {p.price_monthly > 0 ? <><strong>{cf.format(p.price_monthly)}</strong><span>ر.س/شهر</span></> : <strong>مجاني</strong>}
            </div>
            <div className="plat-plan-card__stats">
              <div><strong>{n(p.active_subscribers)}</strong><span>مشترك نشط</span></div>
              <div><strong>{n(p.total_subscribers)}</strong><span>إجمالي</span></div>
            </div>
            {p.description && <p className="plat-plan-card__desc">{p.description}</p>}
            <div className="plat-plan-card__actions">
              <button className="plat-edit-badge-btn" onClick={() => handleEditPlan(p)}>تعديل المميزات والأسعار</button>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Custom plans info */}
      <div className="plat-panel" style={{ marginTop: 24 }}>
        <div className="plat-panel__head"><Settings2 size={18} /><h3>الباقات المخصصة</h3></div>
        <div className="plat-kpis-grid" style={{ gridTemplateColumns: 'repeat(2, 1fr)' }}>
          <KpiCard title="باقات مخصصة نشطة" value={n(data.custom_plans.active_custom)} icon={Zap} color="#8b5cf6" />
          <KpiCard title="إجمالي الباقات المخصصة" value={n(data.custom_plans.total_custom)} icon={Package} color="#3b82f6" />
        </div>
      </div>

      {/* Addons */}
      <div className="plat-panel" style={{ marginTop: 24 }}>
        <div className="plat-panel__head"><Package size={18} /><h3>أسعار الإضافات</h3></div>
        <table className="plat-table plat-table--full">
          <thead><tr><th></th><th>العنصر</th><th>التصنيف</th><th>السعر/وحدة</th><th>الخطوة</th><th>إجراءات</th></tr></thead>
          <tbody>
            {data.addons.map(a => (
              <tr key={a.id}>
                <td>{a.icon}</td>
                <td>{a.label_ar}</td>
                <td><span className="plat-cat-tag">{a.category}</span></td>
                <td><strong>{a.price_per_unit}</strong> ر.س</td>
                <td>{a.step > 1 ? `×${a.step}` : '1'}</td>
                <td className="plat-actions">
                  <button className="plat-act-btn plat-act-btn--warn" onClick={() => handleEditAddon(a)} title="تعديل"><Settings2 size={14} /></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* ── Modal: Edit Plan & Limits ── */}
      {editingPlan && (
        <div className="plat-modal-backdrop">
          <div className="plat-modal">
            <header className="plat-modal__header">
              <h3>تعديل باقة: {editingPlan.name}</h3>
              <button className="plat-modal__close" onClick={() => setEditingPlan(null)}>&times;</button>
            </header>
            <form onSubmit={handleSavePlan} className="plat-modal__body">
              <div className="plat-section-title">بيانات الباقة الأساسية</div>
              
              <div className="plat-form-grid">
                <div className="plat-field">
                  <label className="plat-field__label">اسم الباقة</label>
                  <input className="plat-field__input" value={planForm.name} onChange={e => setPlanForm({...planForm, name: e.target.value})} required />
                </div>
                <div className="plat-field">
                  <label className="plat-field__label">العنوان الفرعي</label>
                  <input className="plat-field__input" value={planForm.subtitle} onChange={e => setPlanForm({...planForm, subtitle: e.target.value})} />
                </div>
              </div>

              <div className="plat-form-grid">
                <div className="plat-field">
                  <label className="plat-field__label">السعر الشهري (ر.س)</label>
                  <input type="number" className="plat-field__input plat-field__input--ltr" value={planForm.price_monthly} onChange={e => setPlanForm({...planForm, price_monthly: parseFloat(e.target.value) || 0})} required />
                </div>
                <div className="plat-field">
                  <label className="plat-field__label">السعر السنوي (ر.س)</label>
                  <input type="number" className="plat-field__input plat-field__input--ltr" value={planForm.price_yearly} onChange={e => setPlanForm({...planForm, price_yearly: parseFloat(e.target.value) || 0})} required />
                </div>
              </div>

              <div className="plat-form-grid">
                <div className="plat-field">
                  <label className="plat-field__label">لون الشارة (HEX)</label>
                  <input className="plat-field__input plat-field__input--ltr" value={planForm.badge_color} onChange={e => setPlanForm({...planForm, badge_color: e.target.value})} required />
                </div>
                <div className="plat-field" style={{ justifyContent: 'center' }}>
                  <label className="plat-field__check">
                    <input type="checkbox" checked={planForm.is_popular} onChange={e => setPlanForm({...planForm, is_popular: e.target.checked})} />
                    <span>تمييز كباقة شعبية (أكثر مبيعاً)</span>
                  </label>
                </div>
              </div>

              <div className="plat-field">
                <label className="plat-field__label">الوصف</label>
                <textarea className="plat-field__input" style={{ minHeight: 60, resize: 'vertical' }} value={planForm.description} onChange={e => setPlanForm({...planForm, description: e.target.value})} />
              </div>

              <div className="plat-section-title">المميزات والحدود البرمجية</div>
              {loadingLimits ? (
                <div className="plat-loading" style={{ padding: 20 }}>جاري تحميل حدود الباقة...</div>
              ) : (
                <div className="plat-limits-list">
                  {planLimits
                    .filter(limit => [
                      'invitations_per_month',
                      'events_per_month',
                      'gates_per_event',
                      'teams_max',
                      'seats_max',
                      'designed_templates'
                    ].includes(limit.key))
                    .sort((a, b) => {
                      const order = [
                        'invitations_per_month',
                        'events_per_month',
                        'gates_per_event',
                        'teams_max',
                        'seats_max',
                        'designed_templates'
                      ];
                      return order.indexOf(a.key) - order.indexOf(b.key);
                    })
                    .map(limit => (
                      <div key={limit.key} className="plat-limit-row">
                        <span>{LIMIT_LABELS[limit.key] || limit.key}</span>
                        <div className="plat-field" style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                          <input
                            type="number"
                            className="plat-field__input plat-field__input--ltr"
                            style={{ width: '100%', padding: '6px 10px' }}
                            value={limit.value}
                            disabled={limit.value === -1}
                            onChange={e => handleLimitChange(limit.key, parseInt(e.target.value) || 0)}
                          />
                        </div>
                        <label className="plat-field__check" style={{ marginTop: 0 }}>
                          <input
                            type="checkbox"
                            checked={limit.value === -1}
                            onChange={e => handleLimitChange(limit.key, e.target.checked ? -1 : 0)}
                          />
                          <span>غير محدود</span>
                        </label>
                      </div>
                    ))}
                </div>
              )}

              <div className="plat-modal__footer" style={{ padding: '16px 0 0', border: 'none', background: 'none' }}>
                <button type="button" className="plat-btn plat-btn--secondary" onClick={() => setEditingPlan(null)}>إلغاء</button>
                <button type="submit" className="plat-btn plat-btn--primary" disabled={savingPlan}>
                  {savingPlan ? 'جاري الحفظ...' : 'حفظ التعديلات'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Modal: Edit Addon Price ── */}
      {editingAddon && (
        <div className="plat-modal-backdrop">
          <div className="plat-modal" style={{ maxWidth: 450 }}>
            <header className="plat-modal__header">
              <h3>تعديل الإضافة: {editingAddon.label_ar}</h3>
              <button className="plat-modal__close" onClick={() => setEditingAddon(null)}>&times;</button>
            </header>
            <form onSubmit={handleSaveAddon} className="plat-modal__body">
              <div className="plat-form-grid plat-form-grid--full">
                <div className="plat-field">
                  <label className="plat-field__label">الاسم بالعربية</label>
                  <input className="plat-field__input" value={addonForm.label_ar} onChange={e => setAddonForm({...addonForm, label_ar: e.target.value})} required />
                </div>
                <div className="plat-field">
                  <label className="plat-field__label">الاسم بالإنجليزية</label>
                  <input className="plat-field__input plat-field__input--ltr" value={addonForm.label_en} onChange={e => setAddonForm({...addonForm, label_en: e.target.value})} required />
                </div>
                <div className="plat-field">
                  <label className="plat-field__label">سعر الوحدة الإضافية (ر.س)</label>
                  <input type="number" step="0.01" className="plat-field__input plat-field__input--ltr" value={addonForm.price_per_unit} onChange={e => setAddonForm({...addonForm, price_per_unit: parseFloat(e.target.value) || 0})} required />
                </div>
                <div className="plat-form-grid" style={{ marginBottom: 0 }}>
                  <div className="plat-field">
                    <label className="plat-field__label">وحدة القياس</label>
                    <input className="plat-field__input" value={addonForm.unit_ar} onChange={e => setAddonForm({...addonForm, unit_ar: e.target.value})} required />
                  </div>
                  <div className="plat-field">
                    <label className="plat-field__label">الرمز (Icon)</label>
                    <input className="plat-field__input" value={addonForm.icon} onChange={e => setAddonForm({...addonForm, icon: e.target.value})} required />
                  </div>
                </div>
              </div>

              <div className="plat-modal__footer" style={{ padding: '16px 0 0', border: 'none', background: 'none' }}>
                <button type="button" className="plat-btn plat-btn--secondary" onClick={() => setEditingAddon(null)}>إلغاء</button>
                <button type="submit" className="plat-btn plat-btn--primary" disabled={savingAddon}>
                  {savingAddon ? 'جاري الحفظ...' : 'حفظ التعديلات'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

/* ══════════════════════════════════════════════════
   TAB: SUBSCRIPTIONS
   ══════════════════════════════════════════════════ */
function SubscriptionsTab() {
  const [planFilter, setPlanFilter] = useState('')
  const { data: subs = [], isLoading } = useQuery({
    queryKey: ['platform-subs', planFilter],
    queryFn: () => platformAPI.listSubscriptions({ plan_code: planFilter || undefined, limit: 100 }),
  })

  return (
    <div className="plat-tab-content">
      <div className="plat-toolbar">
        <select value={planFilter} onChange={e => setPlanFilter(e.target.value)}>
          <option value="">كل الباقات</option>
          <option value="starter">Starter</option>
          <option value="basic">Basic</option>
          <option value="pro">Pro</option>
          <option value="business">Business</option>
          <option value="enterprise">Enterprise</option>
        </select>
      </div>
      {isLoading ? <div className="plat-loading">جار التحميل...</div> : (
        <table className="plat-table plat-table--full">
          <thead><tr><th>المؤسسة</th><th>الباقة</th><th>السعر</th><th>الحالة</th><th>نهاية الفترة</th><th>التاريخ</th></tr></thead>
          <tbody>
            {subs.map(s => (
              <tr key={s.id}>
                <td><strong>{s.tenant_name}</strong><br /><small className="plat-mono">{s.tenant_slug}</small></td>
                <td><span className="plat-plan-tag">{s.plan_name}</span></td>
                <td>{s.price_monthly > 0 ? currency(s.price_monthly) : 'مجاني'}</td>
                <td><StatusBadge status={s.sub_status} /></td>
                <td className="plat-date">{s.current_period_end ? new Date(s.current_period_end).toLocaleDateString('ar-SA') : '—'}</td>
                <td className="plat-date">{new Date(s.created_at).toLocaleDateString('ar-SA')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

/* ══════════════════════════════════════════════════
   TAB: AUDIT
   ══════════════════════════════════════════════════ */
function AuditTab() {
  const [actionFilter, setActionFilter] = useState('')
  const { data: logs = [], isLoading } = useQuery({
    queryKey: ['platform-audit', actionFilter],
    queryFn: () => platformAPI.listAuditLogs({ action: actionFilter || undefined, limit: 100 }),
  })

  return (
    <div className="plat-tab-content">
      <div className="plat-toolbar">
        <div className="plat-search-wrap"><Search size={16} /><input placeholder="بحث بالإجراء..." value={actionFilter} onChange={e => setActionFilter(e.target.value)} /></div>
      </div>
      {isLoading ? <div className="plat-loading">جار التحميل...</div> : (
        <table className="plat-table plat-table--full">
          <thead><tr><th>الإجراء</th><th>المنفذ</th><th>المؤسسة</th><th>النوع</th><th>IP</th><th>التاريخ</th></tr></thead>
          <tbody>
            {logs.map(l => (
              <tr key={l.id}>
                <td><span className="plat-action-tag">{l.action}</span></td>
                <td>{l.actor_name || '—'}</td>
                <td>{l.tenant_name || '—'}</td>
                <td className="plat-mono">{l.resource_type}</td>
                <td className="plat-mono">{l.ip_address || '—'}</td>
                <td className="plat-date">{new Date(l.created_at).toLocaleDateString('ar-SA', { hour: '2-digit', minute: '2-digit' })}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

/* ══════════════════════════════════════════════════════════════
   ██ PLATFORM ADMIN PAGE
   ══════════════════════════════════════════════════════════════ */

export default function PlatformAdminPage() {
  const [activeTab, setActiveTab] = useState<TabKey>('overview')
  const clearAuth = useAuthStore(s => s.clearAuth)
  const user = useAuthStore(s => s.user)

  const { data: analytics, isLoading: analyticsLoading, refetch } = useQuery({
    queryKey: ['platform-analytics'],
    queryFn: platformAPI.analytics,
  })

  return (
    <div className="plat-shell" dir="rtl">
      {/* ── Sidebar ── */}
      <aside className="plat-sidebar">
        <div className="plat-brand">
          <div className="plat-brand__icon"><Shield size={24} /></div>
          <div>
            <strong>Qentry</strong>
            <span>إدارة المنصة</span>
          </div>
        </div>

        <nav className="plat-nav">
          {TABS.map(tab => (
            <button
              key={tab.key}
              className={`plat-nav__item${activeTab === tab.key ? ' plat-nav__item--active' : ''}`}
              onClick={() => setActiveTab(tab.key)}
            >
              <tab.icon size={18} />{tab.label}
            </button>
          ))}
        </nav>

        <div className="plat-sidebar__footer">
          <NavLink to="/dashboard" className="plat-nav__item"><Globe size={18} />لوحة التحكم</NavLink>
          <button className="plat-nav__item plat-nav__item--danger" onClick={clearAuth}><LogOut size={18} />تسجيل الخروج</button>
        </div>
      </aside>

      {/* ── Main Content ── */}
      <main className="plat-main">
        <header className="plat-header">
          <div>
            <span className="plat-header__kicker">إدارة المنصة</span>
            <h1>{TABS.find(t => t.key === activeTab)?.label}</h1>
          </div>
          <div className="plat-header__actions">
            <span className="plat-user-badge"><Crown size={14} />{user?.full_name || 'مشرف'}</span>
            <button className="plat-refresh-btn" onClick={() => refetch()}><RefreshCcw size={16} /></button>
          </div>
        </header>

        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.25 }}
          >
            {activeTab === 'overview' && (analyticsLoading ? <div className="plat-loading">جار تحميل التحليلات...</div> : analytics ? <OverviewTab data={analytics} /> : null)}
            {activeTab === 'tenants' && <TenantsTab />}
            {activeTab === 'users' && <UsersTab />}
            {activeTab === 'roles' && <PlatformRolesTab />}
            {activeTab === 'plans' && <PlansTab />}
            {activeTab === 'subscriptions' && <SubscriptionsTab />}
            {activeTab === 'audit' && <AuditTab />}
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  )
}
