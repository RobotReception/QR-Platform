/**
 * EventsPage.tsx
 * Clean orchestrator — data fetching delegated to useEventsList hook,
 * UI state delegated to useEventsStore, rendering delegated to components.
 */
import { useState } from 'react'
import { Plus, CalendarDays, Search, Filter, RefreshCw } from 'lucide-react'
import { WorkspaceShell } from '@features/workspace/components/WorkspaceShell'
import { useAuthStore } from '@features/auth/store/authStore'
import { useEventsList } from '../hooks/useEvents'
import { useEventsStore } from '../store/eventsStore'
import { EventCard } from '../components/EventCard'
import { EventSkeletonGrid } from '../components/EventSkeletonCard'
import { CreateEventDialog } from '../components/CreateEventDialog'
import type { EventStatus } from '../types'
import '@features/users/pages/users.css'
import './events.css'

const STATUS_OPTIONS: { value: EventStatus | ''; label: string }[] = [
  { value: '', label: 'جميع الحالات' },
  { value: 'draft', label: 'مسودة' },
  { value: 'published', label: 'منشور' },
  { value: 'active', label: 'نشط' },
  { value: 'completed', label: 'مكتمل' },
  { value: 'cancelled', label: 'ملغي' },
]

export default function EventsPage() {
  const currentTenantId = useAuthStore((s) => s.currentTenantId)
  const [showCreateDialog, setShowCreateDialog] = useState(false)

  // UI state from Zustand
  const { searchQuery, statusFilter, setSearchQuery, setStatusFilter } = useEventsStore()

  // Server state from React Query
  const { data: events, isLoading, isError, refetch } = useEventsList(
    currentTenantId,
    statusFilter,
  )

  if (!currentTenantId) {
    return (
      <WorkspaceShell title="الأحداث" subtitle="">
        <div className="dash-state">
          <CalendarDays size={40} />
          <h1>لا توجد مساحة عمل محددة</h1>
          <p>اختر مساحة العمل لعرض قائمة الأحداث.</p>
        </div>
      </WorkspaceShell>
    )
  }

  // Client-side search filter (status filtering is server-side via query param)
  const filtered = events?.filter((e) => {
    if (!searchQuery.trim()) return true
    const q = searchQuery.toLowerCase()
    return (
      e.title.toLowerCase().includes(q) ||
      (e.venue_name?.toLowerCase().includes(q) ?? false) ||
      (e.venue_city?.toLowerCase().includes(q) ?? false)
    )
  })

  return (
    <WorkspaceShell
      title="الأحداث"
      subtitle="إدارة كافة الفعاليات والمناسبات الخاصة بمساحة العمل"
      actions={
        <button className="btn btn-primary" onClick={() => setShowCreateDialog(true)}>
          <Plus size={18} />
          حدث جديد
        </button>
      }
    >
      {/* ── Toolbar ── */}
      <div className="users-toolbar">
        <div className="toolbar-search">
          <Search size={17} className="search-icon" />
          <input
            id="events-search"
            type="text"
            className="users-search"
            placeholder="بحث بالاسم أو المدينة…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            aria-label="بحث في الأحداث"
          />
        </div>

        <div className="toolbar-filters">
          <div style={{ position: 'relative' }}>
            <Filter
              size={15}
              style={{
                position: 'absolute',
                right: '12px',
                top: '50%',
                transform: 'translateY(-50%)',
                color: 'var(--color-text-muted)',
                pointerEvents: 'none',
              }}
            />
            <select
              id="events-status-filter"
              className="filter-select"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as EventStatus | '')}
              style={{ paddingRight: '36px' }}
              aria-label="فلترة حسب الحالة"
            >
              {STATUS_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* ── States ── */}
      {isLoading ? (
        <EventSkeletonGrid count={6} />
      ) : isError ? (
        <ErrorState onRetry={refetch} />
      ) : !filtered?.length ? (
        <EmptyState
          hasFilters={Boolean(searchQuery || statusFilter)}
          onCreate={() => setShowCreateDialog(true)}
          onClear={() => { setSearchQuery(''); setStatusFilter('') }}
        />
      ) : (
        <div className="events-grid">
          {filtered.map((event) => (
            <EventCard key={event.id} event={event} />
          ))}
        </div>
      )}

      {/* ── Create Dialog ── */}
      {showCreateDialog && (
        <CreateEventDialog
          isOpen={showCreateDialog}
          onClose={() => setShowCreateDialog(false)}
        />
      )}
    </WorkspaceShell>
  )
}

// ── Error State ──────────────────────────────────────────────────
function ErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="events-empty-state">
      <div className="events-empty-state__icon">
        <CalendarDays size={36} />
      </div>
      <h3>فشل تحميل الأحداث</h3>
      <p>تعذّر الاتصال بالخادم. يُرجى التحقق من الاتصال والمحاولة مجدداً.</p>
      <button className="btn btn-ghost" onClick={onRetry}>
        <RefreshCw size={16} />
        إعادة المحاولة
      </button>
    </div>
  )
}

// ── Empty State ──────────────────────────────────────────────────
function EmptyState({
  hasFilters,
  onCreate,
  onClear,
}: {
  hasFilters: boolean
  onCreate: () => void
  onClear: () => void
}) {
  return (
    <div className="events-empty-state">
      <div className="events-empty-state__icon">
        <CalendarDays size={36} />
      </div>
      {hasFilters ? (
        <>
          <h3>لا توجد نتائج مطابقة</h3>
          <p>لم يتم العثور على أحداث تطابق معايير البحث المحددة.</p>
          <button className="btn btn-ghost" onClick={onClear}>
            إلغاء الفلاتر
          </button>
        </>
      ) : (
        <>
          <h3>لا توجد أحداث بعد</h3>
          <p>ابدأ بإنشاء أول فعالية أو مناسبة لمساحة العمل هذه.</p>
          <button className="btn btn-primary" onClick={onCreate}>
            <Plus size={16} />
            إنشاء حدث جديد
          </button>
        </>
      )}
    </div>
  )
}
