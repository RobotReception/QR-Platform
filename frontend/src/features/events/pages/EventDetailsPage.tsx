/**
 * EventDetailsPage.tsx
 * Clean orchestrator for the event detail view.
 * All business logic lives in hooks; all UI lives in components.
 */
import { useState } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { WorkspaceShell } from '@features/workspace/components/WorkspaceShell'
import { useAuthStore } from '@features/auth/store/authStore'
import {
  useEventDetail,
  useEventStats,
  useEventPublish,
} from '../hooks/useEventDetails'
import { EventStatsStrip } from '../components/EventStatsStrip'
import { EventSettingsForm } from '../components/EventSettingsForm'
import { EventGatesTab } from '../components/EventGatesTab'
import { EventInvitationsTab } from '../components/EventInvitationsTab'
import { EventBarcodesTab } from '../components/EventBarcodesTab'
import { EventTemplatesTab } from '../components/EventTemplatesTab'
import { ConfirmDialog } from '../components/ConfirmDialog'
import { getStatusConfig, formatDateFull } from '../utils/eventUtils'
import {
  Loader2,
  ArrowRight,
  Globe,
  Settings,
  DoorOpen,
  MapPin,
  CalendarDays,
  QrCode,
  Printer,
  Palette,
} from 'lucide-react'
import '@features/users/pages/users.css'
import './events.css'

type Tab = 'overview' | 'gates' | 'invitations' | 'barcodes' | 'templates'

export default function EventDetailsPage() {
  const { eventId } = useParams<{ eventId: string }>()
  const navigate = useNavigate()
  const currentTenantId = useAuthStore((s) => s.currentTenantId)

  const [searchParams] = useSearchParams()
  const tabFromUrl = searchParams.get('tab') as Tab | null
  const [activeTab, setActiveTab] = useState<Tab>(tabFromUrl && ['overview', 'gates', 'invitations', 'barcodes', 'templates'].includes(tabFromUrl) ? tabFromUrl : 'overview')
  const [showPublishConfirm, setShowPublishConfirm] = useState(false)
  const clearAuth = useAuthStore((s) => s.clearAuth)

  // ── Data ──────────────────────────────────────────────────────
  const { data: event, isLoading } = useEventDetail(currentTenantId, eventId)
  const { data: stats, isLoading: isLoadingStats } = useEventStats(eventId)
  const publishMutation = useEventPublish(currentTenantId, eventId)

  if (!currentTenantId) {
    return (
      <WorkspaceShell title="لا توجد مساحة عمل" subtitle="">
        <div className="dash-state">
          <QrCode size={40} />
          <h1>لا توجد مساحة عمل محددة</h1>
          <p>اختر مساحة العمل أو سجّل الدخول من جديد لعرض بيانات الحدث.</p>
          <div className="header-actions">
            <button className="btn btn-primary" onClick={() => navigate('/dashboard')}>
              العودة للوحة التحكم
            </button>
            <button className="btn btn-ghost" onClick={clearAuth}>
              تسجيل الخروج
            </button>
          </div>
        </div>
      </WorkspaceShell>
    )
  }

  // ── Loading ───────────────────────────────────────────────────
  if (isLoading) {
    return (
      <WorkspaceShell title="جاري التحميل…" subtitle="">
        <div className="center-loader" style={{ paddingTop: 80 }}>
          <Loader2 size={36} className="spin" />
          <span>جاري تحميل بيانات الحدث…</span>
        </div>
      </WorkspaceShell>
    )
  }

  // ── Not Found ─────────────────────────────────────────────────
  if (!event) {
    return (
      <WorkspaceShell title="خطأ" subtitle="">
        <div className="events-empty-state">
          <CalendarDays size={48} style={{ opacity: 0.4 }} />
          <h3>الحدث غير موجود</h3>
          <p>ربما تم حذف هذا الحدث أو أن الرابط غير صحيح.</p>
          <button className="btn btn-ghost" onClick={() => navigate('/events')}>
            <ArrowRight size={16} />
            العودة للأحداث
          </button>
        </div>
      </WorkspaceShell>
    )
  }

  const { label: statusLabel, css: statusCss } = getStatusConfig(event.status)

  return (
    <WorkspaceShell
      title={event.title}
      subtitle="تفاصيل وإعدادات الحدث"
      actions={
        <div className="header-actions">
          {/* Publish Button — shown only when draft */}
          {event.status === 'draft' && (
            <button
              className="btn btn-primary"
              onClick={() => setShowPublishConfirm(true)}
              disabled={publishMutation.isPending}
            >
              {publishMutation.isPending ? (
                <Loader2 size={16} className="spin" />
              ) : (
                <Globe size={16} />
              )}
              نشر الحدث
            </button>
          )}

          {/* Back button */}
          <button className="btn btn-ghost" onClick={() => navigate('/events')}>
            عودة
            <ArrowRight size={16} style={{ marginRight: 6, marginLeft: 0 }} />
          </button>
        </div>
      }
    >
      {/* ── Event Header Card ── */}
      <div className="event-details-header">
        <div className="event-details-title">
          {/* Status + Slug row */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 10 }}>
            <span className={`event-card__status status-badge--${statusCss}`} style={{ position: 'relative', top: 0, right: 0 }}>
              {statusLabel}
            </span>
            {event.slug && (
              <a
                href={`/e/${event.slug}`}
                target="_blank"
                rel="noreferrer"
                style={{ fontSize: 12, color: 'var(--color-primary-light)', display: 'flex', alignItems: 'center', gap: 4 }}
              >
                <Globe size={13} />
                /e/{event.slug}
              </a>
            )}
          </div>

          <h1>{event.title}</h1>

          {/* Date + Venue */}
          <div className="meta-row">
            <span>
              <CalendarDays size={14} />
              {formatDateFull(event.start_date)}
            </span>
            {event.venue_name && (
              <span>
                <MapPin size={14} />
                {event.venue_name}
                {event.venue_city ? `، ${event.venue_city}` : ''}
              </span>
            )}
          </div>
        </div>

        {/* ── Stats Strip ── */}
        <EventStatsStrip event={event} stats={stats} isLoading={isLoadingStats} />
      </div>

      {/* ── Tabs ── */}
      <div className="event-tabs" role="tablist">
        <button
          id="tab-overview"
          className={`event-tab ${activeTab === 'overview' ? 'event-tab--active' : ''}`}
          onClick={() => setActiveTab('overview')}
          role="tab"
          aria-selected={activeTab === 'overview'}
          aria-controls="panel-overview"
        >
          <Settings size={15} />
          إعدادات الحدث
        </button>
        <button
          id="tab-gates"
          className={`event-tab ${activeTab === 'gates' ? 'event-tab--active' : ''}`}
          onClick={() => setActiveTab('gates')}
          role="tab"
          aria-selected={activeTab === 'gates'}
          aria-controls="panel-gates"
        >
          <DoorOpen size={15} />
          بوابات الدخول
        </button>
        <button
          id="tab-invitations"
          className={`event-tab ${activeTab === 'invitations' ? 'event-tab--active' : ''}`}
          onClick={() => setActiveTab('invitations')}
          role="tab"
          aria-selected={activeTab === 'invitations'}
          aria-controls="panel-invitations"
        >
          <Printer size={15} />
          إنشاء الدعوات
        </button>
        <button
          id="tab-barcodes"
          className={`event-tab ${activeTab === 'barcodes' ? 'event-tab--active' : ''}`}
          onClick={() => setActiveTab('barcodes')}
          role="tab"
          aria-selected={activeTab === 'barcodes'}
          aria-controls="panel-barcodes"
        >
          <QrCode size={15} />
          قائمة الدعوات
        </button>
        <button
          id="tab-templates"
          className={`event-tab ${activeTab === 'templates' ? 'event-tab--active' : ''}`}
          onClick={() => setActiveTab('templates')}
          role="tab"
          aria-selected={activeTab === 'templates'}
          aria-controls="panel-templates"
        >
          <Palette size={15} />
          قوالب الحفل
        </button>
      </div>

      {/* ── Tab Panels ── */}
      <div id="panel-overview" role="tabpanel" aria-labelledby="tab-overview" hidden={activeTab !== 'overview'}>
        {activeTab === 'overview' && (
          <EventSettingsForm event={event} tenantId={currentTenantId} />
        )}
      </div>

      <div id="panel-gates" role="tabpanel" aria-labelledby="tab-gates" hidden={activeTab !== 'gates'}>
        {activeTab === 'gates' && (
          <EventGatesTab eventId={event.id} isActiveTab={activeTab === 'gates'} />
        )}
      </div>

      <div id="panel-invitations" role="tabpanel" aria-labelledby="tab-invitations" hidden={activeTab !== 'invitations'}>
        {activeTab === 'invitations' && (
          <EventInvitationsTab event={event} stats={stats} />
        )}
      </div>

      <div id="panel-barcodes" role="tabpanel" aria-labelledby="tab-barcodes" hidden={activeTab !== 'barcodes'}>
        {activeTab === 'barcodes' && (
          <EventBarcodesTab event={event} stats={stats} onlyHistory />
        )}
      </div>

      <div id="panel-templates" role="tabpanel" aria-labelledby="tab-templates" hidden={activeTab !== 'templates'}>
        {activeTab === 'templates' && (
          <EventTemplatesTab eventId={event.id} isActiveTab={activeTab === 'templates'} />
        )}
      </div>

      {/* ── Publish Confirmation ── */}
      <ConfirmDialog
        isOpen={showPublishConfirm}
        title="نشر الحدث"
        message={`هل أنت متأكد من نشر حدث "${event.title}"؟ بعد النشر، سيتمكن الضيوف من رؤية الدعوات وتأكيد حضورهم.`}
        confirmLabel="نعم، انشر الآن"
        variant="default"
        isPending={publishMutation.isPending}
        onConfirm={() => {
          publishMutation.mutate(undefined, {
            onSuccess: () => setShowPublishConfirm(false),
          })
        }}
        onCancel={() => setShowPublishConfirm(false)}
      />
    </WorkspaceShell>
  )
}
