/**
 * InvitationsPage.tsx
 * Main invitations management page with filters, search, and CRUD actions.
 */
import { useState, useMemo } from 'react'
import {
  Ticket, Search, Plus, Zap, Send, Ban,
  RefreshCw, Loader2, CalendarDays,
} from 'lucide-react'
import { WorkspaceShell } from '@features/workspace/components/WorkspaceShell'
import { useAuthStore } from '@features/auth/store/authStore'
import { useInvitationsList, useRevokeInvitation } from '../hooks/useInvitations'
import { InvitationCard } from '../components/InvitationCard'
import { CreateInvitationDialog } from '../components/CreateInvitationDialog'
import { QuickInviteDialog } from '../components/QuickInviteDialog'
import { SendInvitationsDialog } from '../components/SendInvitationsDialog'
import { InvitationDetailPanel } from '../components/InvitationDetailPanel'
import type { Invitation, InvitationStatus, TicketClass, InvitationListParams } from '../types'
import { useEventsList } from '@features/events/hooks/useEvents'
import { useNavigate } from 'react-router-dom'
import './invitations.css'

const STATUS_OPTIONS: { value: InvitationStatus | ''; label: string }[] = [
  { value: '', label: 'جميع الحالات' },
  { value: 'created', label: 'مُنشأة' },
  { value: 'sent', label: 'مُرسلة' },
  { value: 'viewed', label: 'مُشاهدة' },
  { value: 'accepted', label: 'مقبولة' },
  { value: 'declined', label: 'مرفوضة' },
  { value: 'checked_in', label: 'حاضر' },
  { value: 'revoked', label: 'ملغاة' },
]

const CLASS_OPTIONS: { value: TicketClass | ''; label: string }[] = [
  { value: '', label: 'جميع الأنواع' },
  { value: 'vip', label: 'VIP' },
  { value: 'normal', label: 'عادي' },
]

export default function InvitationsPage() {
  const tenantId = useAuthStore((s) => s.currentTenantId)
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<InvitationStatus | ''>('')
  const [classFilter, setClassFilter] = useState<TicketClass | ''>('')
  const [eventFilter, setEventFilter] = useState('')
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [viewingInv, setViewingInv] = useState<Invitation | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [showQuick, setShowQuick] = useState(false)
  const [showSend, setShowSend] = useState(false)
  const [viewMode, setViewMode] = useState<'all' | 'requests'>('all')

  const params: InvitationListParams = {
    ...(eventFilter && { event_id: eventFilter }),
    ...(statusFilter && { status: statusFilter }),
    ...(classFilter && { ticket_class: classFilter }),
    limit: 200,
  }
  const { data: invitations, isLoading, isError, refetch } = useInvitationsList(params)
  const { data: events } = useEventsList(tenantId || '', '')
  const revokeMutation = useRevokeInvitation()

  const hasEvents = events && events.length > 0
  const eventOptions = useMemo(
    () => (events || []).map((e) => ({ id: e.id, title: e.title })),
    [events]
  )

  const filtered = useMemo(() => {
    if (!invitations) return []
    let list = invitations
    if (viewMode === 'requests') {
      list = list.filter((inv) => inv.rsvp_status === 'pending')
    }
    if (!search.trim()) return list
    const q = search.toLowerCase()
    return list.filter((inv) =>
      inv.guest_name?.toLowerCase().includes(q) ||
      inv.guest_name_ar?.includes(q) ||
      inv.guest_phone?.includes(q) ||
      inv.token?.includes(q)
    )
  }, [invitations, search, viewMode])

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const selectAll = () => {
    if (selectedIds.size === filtered.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(filtered.map((i) => i.id)))
    }
  }

  const handleRevoke = (id: string) => {
    if (confirm('هل تريد إلغاء هذه الدعوة؟')) {
      revokeMutation.mutate(id)
    }
  }

  const openCreate = () => {
    if (!hasEvents) {
      if (confirm('لا توجد أحداث. هل تريد إنشاء حدث جديد أولاً؟')) {
        navigate('/events')
      }
      return
    }
    setShowCreate(true)
  }

  const openQuick = () => {
    if (!hasEvents) {
      if (confirm('لا توجد أحداث. هل تريد إنشاء حدث جديد أولاً؟')) {
        navigate('/events')
      }
      return
    }
    setShowQuick(true)
  }

  if (!tenantId) {
    return (
      <WorkspaceShell title="الدعوات" subtitle="">
        <div className="dash-state">
          <Zap size={40} />
          <h1>لا توجد مساحة عمل محددة</h1>
          <p>اختر مساحة العمل حتى تظهر الدعوات والبيانات.</p>
        </div>
      </WorkspaceShell>
    )
  }

  return (
    <WorkspaceShell
      title="الدعوات"
      subtitle="إدارة جميع الدعوات الرقمية لفعالياتك"
      actions={
        <div className="inv-page-actions">
          <button className="btn btn-ghost" onClick={openQuick}>
            <Zap size={16} /> دعوات سريعة
          </button>
          <button className="btn btn-primary" onClick={openCreate}>
            <Plus size={16} /> دعوة جديدة
          </button>
        </div>
      }
    >
      {/* View Mode Tabs */}
      <div className="inv-view-tabs" style={{ display: 'flex', gap: 16, borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: '12px', marginBottom: '16px' }}>
        <button
          className={`tab-btn ${viewMode === 'all' ? 'active' : ''}`}
          onClick={() => setViewMode('all')}
          style={{
            background: 'transparent',
            border: 'none',
            color: viewMode === 'all' ? '#C9A96E' : '#9ca3af',
            fontSize: '0.95rem',
            fontWeight: 'bold',
            cursor: 'pointer',
            padding: '4px 12px',
            borderBottom: viewMode === 'all' ? '2px solid #C9A96E' : 'none',
            transition: 'all 0.2s'
          }}
        >
          جميع الحضور والمدعوين
        </button>
        <button
          className={`tab-btn ${viewMode === 'requests' ? 'active' : ''}`}
          onClick={() => setViewMode('requests')}
          style={{
            background: 'transparent',
            border: 'none',
            color: viewMode === 'requests' ? '#C9A96E' : '#9ca3af',
            fontSize: '0.95rem',
            fontWeight: 'bold',
            cursor: 'pointer',
            padding: '4px 12px',
            borderBottom: viewMode === 'requests' ? '2px solid #C9A96E' : 'none',
            transition: 'all 0.2s',
            display: 'flex',
            alignItems: 'center',
            gap: 6
          }}
        >
          <span>طلبات التسجيل قيد المراجعة</span>
          {invitations?.filter((inv) => inv.rsvp_status === 'pending').length ? (
            <span style={{
              background: '#C9A96E',
              color: '#0f172a',
              fontSize: '0.72rem',
              padding: '2px 6px',
              borderRadius: '10px',
              fontWeight: 800
            }}>
              {invitations.filter((inv) => inv.rsvp_status === 'pending').length}
            </span>
          ) : null}
        </button>
      </div>

      {/* ── Toolbar ── */}
      <div className="inv-toolbar">
        <div className="inv-toolbar__search">
          <Search size={17} className="search-icon" />
          <input
            type="text"
            placeholder="بحث بالاسم أو الهاتف أو الرمز..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div className="inv-toolbar__filters">
          {/* Event filter */}
          <select
            value={eventFilter}
            onChange={(e) => setEventFilter(e.target.value)}
            className="inv-filter-select"
          >
            <option value="">جميع الأحداث</option>
            {events?.map((ev) => (
              <option key={ev.id} value={ev.id}>{ev.title}</option>
            ))}
          </select>

          {/* Status filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as any)}
            className="inv-filter-select"
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>

          {/* Class filter */}
          <select
            value={classFilter}
            onChange={(e) => setClassFilter(e.target.value as any)}
            className="inv-filter-select"
          >
            {CLASS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* ── Bulk Actions Bar ── */}
      {selectedIds.size > 0 && (
        <div className="inv-bulk-bar">
          <span>{selectedIds.size} دعوة محددة</span>
          <button className="btn btn-ghost btn--sm" onClick={() => setShowSend(true)}>
            <Send size={14} /> إرسال
          </button>
          <button
            className="btn btn-ghost btn--sm btn--danger"
            onClick={() => {
              if (confirm(`إلغاء ${selectedIds.size} دعوة؟`)) {
                selectedIds.forEach((id) => revokeMutation.mutate(id))
                setSelectedIds(new Set())
              }
            }}
          >
            <Ban size={14} /> إلغاء الكل
          </button>
          <button className="btn btn-ghost btn--sm" onClick={() => setSelectedIds(new Set())}>
            إلغاء التحديد
          </button>
        </div>
      )}

      {/* ── List ── */}
      {isLoading ? (
        <div className="inv-loading">
          <Loader2 size={32} className="animate-spin" />
          <span>جاري تحميل الدعوات...</span>
        </div>
      ) : isError ? (
        <div className="inv-empty">
          <Ticket size={36} />
          <h3>فشل تحميل الدعوات</h3>
          <p>تعذّر الاتصال بالخادم</p>
          <button className="btn btn-ghost" onClick={() => refetch()}>
            <RefreshCw size={16} /> إعادة المحاولة
          </button>
        </div>
      ) : !filtered.length ? (
        <div className="inv-empty">
          {hasEvents ? (
            <>
              <Ticket size={36} />
              <h3>{search || statusFilter || classFilter || eventFilter ? 'لا توجد نتائج' : 'لا توجد دعوات بعد'}</h3>
              <p>
                {search || statusFilter || classFilter || eventFilter
                  ? 'لم يتم العثور على دعوات تطابق معايير البحث'
                  : 'ابدأ بإنشاء أول دعوة لفعالياتك'}
              </p>
              {!search && !statusFilter && !classFilter && !eventFilter && (
                <button className="btn btn-primary" onClick={openCreate}>
                  <Plus size={16} /> إنشاء دعوة
                </button>
              )}
            </>
          ) : (
            <>
              <CalendarDays size={36} />
              <h3>لا توجد أحداث</h3>
              <p>أنشئ حدثاً أولاً ثم يمكنك إنشاء دعوات له</p>
              <button className="btn btn-primary" onClick={() => navigate('/events')}>
                <CalendarDays size={16} /> إنشاء حدث
              </button>
            </>
          )}
        </div>
      ) : (
        <div className="inv-list">
          {/* Header */}
          <div className="inv-list-header">
            <label className="inv-list-header__check">
              <input type="checkbox" checked={selectedIds.size === filtered.length && filtered.length > 0} onChange={selectAll} />
            </label>
            <span className="inv-list-header__count">{filtered.length} دعوة</span>
          </div>
          {filtered.map((inv) => (
            <InvitationCard
              key={inv.id}
              invitation={inv}
              selected={selectedIds.has(inv.id)}
              onSelect={toggleSelect}
              onView={setViewingInv}
              onRevoke={handleRevoke}
            />
          ))}
        </div>
      )}

      {/* ── Dialogs ── */}
      <CreateInvitationDialog
        isOpen={showCreate}
        onClose={() => { setShowCreate(false); refetch() }}
        eventId={eventFilter || undefined}
        eventTitle={eventFilter ? events?.find((e) => e.id === eventFilter)?.title : undefined}
        events={eventOptions}
      />
      <QuickInviteDialog
        isOpen={showQuick}
        onClose={() => { setShowQuick(false); refetch() }}
        eventId={eventFilter || undefined}
        events={eventOptions}
      />
      {showSend && (
        <SendInvitationsDialog
          isOpen={showSend}
          onClose={() => { setShowSend(false); refetch() }}
          selectedIds={Array.from(selectedIds)}
        />
      )}
      <InvitationDetailPanel
        invitation={viewingInv}
        onClose={() => setViewingInv(null)}
      />
    </WorkspaceShell>
  )
}
