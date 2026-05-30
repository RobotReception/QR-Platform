/**
 * EventGatesTab.tsx
 * Gates management tab — extracted from EventDetailsPage.
 * Uses ConfirmDialog instead of window.confirm().
 */
import { useState } from 'react'
import { DoorOpen, Loader2, Trash2, ShieldCheck } from 'lucide-react'
import { useEventGates, useGateDelete } from '../hooks/useEventDetails'
import { CreateGateDialog } from './CreateGateDialog'
import { ConfirmDialog } from './ConfirmDialog'
import { formatDateShort } from '../utils/eventUtils'

interface Props {
  eventId: string
  isActiveTab: boolean
}

export function EventGatesTab({ eventId, isActiveTab }: Props) {
  const [showCreate, setShowCreate] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; name: string } | null>(null)

  const { data: gates, isLoading } = useEventGates(eventId, isActiveTab)
  const deleteMutation = useGateDelete(eventId)

  const handleConfirmDelete = () => {
    if (!deleteTarget) return
    deleteMutation.mutate(deleteTarget.id, {
      onSuccess: () => setDeleteTarget(null),
    })
  }

  return (
    <div className="event-form-section">
      {/* ── Header ── */}
      <div className="event-section-header">
        <h3 className="section-title">
          <DoorOpen size={18} />
          بوابات الدخول للحدث
        </h3>
        <button className="btn btn-primary btn-sm" onClick={() => setShowCreate(true)}>
          <DoorOpen size={14} />
          إضافة بوابة
        </button>
      </div>

      {/* ── Content ── */}
      {isLoading ? (
        <div className="center-loader">
          <Loader2 size={28} className="spin" />
          <span>جاري التحميل…</span>
        </div>
      ) : !gates?.length ? (
        <div className="gates-empty-state">
          <ShieldCheck size={40} />
          <p>لا توجد بوابات مخصصة</p>
          <span>سيتم استخدام البوابة الرئيسية افتراضياً لجميع الضيوف.</span>
        </div>
      ) : (
        <div className="gates-list">
          {/* Header row */}
          <div className="gates-list__head">
            <div>اسم البوابة</div>
            <div>الفئات المسموح لها</div>
            <div>تاريخ الإنشاء</div>
            <div style={{ textAlign: 'center' }}>إجراء</div>
          </div>

          {/* Data rows */}
          {gates.map((gate) => (
            <div key={gate.id} className="gates-list__row">
              <div className="gates-list__name">
                <DoorOpen size={14} style={{ color: 'var(--color-primary-light)', flexShrink: 0 }} />
                <strong>{gate.name}</strong>
                {gate.name_ar && <span className="gates-list__name-ar">{gate.name_ar}</span>}
              </div>

              <div className="gates-list__classes">
                {gate.allowed_classes?.map((c) => (
                  <span
                    key={c}
                    className={`users-chip ${c === 'vip' ? 'users-chip--owner' : 'users-chip--member'}`}
                  >
                    {c === 'vip' ? '👑 VIP' : '🎫 عادي'}
                  </span>
                ))}
              </div>

              <div className="date-cell">{formatDateShort(gate.created_at)}</div>

              <div style={{ textAlign: 'center' }}>
                <button
                  className="action-btn action-btn--danger"
                  onClick={() => setDeleteTarget({ id: gate.id, name: gate.name })}
                  title="حذف البوابة"
                >
                  <Trash2 size={15} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── Dialogs ── */}
      {showCreate && (
        <CreateGateDialog
          eventId={eventId}
          isOpen={showCreate}
          onClose={() => setShowCreate(false)}
        />
      )}

      <ConfirmDialog
        isOpen={Boolean(deleteTarget)}
        title="حذف البوابة"
        message={`هل أنت متأكد من حذف بوابة "${deleteTarget?.name}"؟ لا يمكن التراجع عن هذا الإجراء.`}
        confirmLabel="نعم، احذف"
        variant="danger"
        isPending={deleteMutation.isPending}
        onConfirm={handleConfirmDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  )
}
