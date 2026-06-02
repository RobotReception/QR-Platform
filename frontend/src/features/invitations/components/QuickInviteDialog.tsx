import { useState } from 'react'
import { X, Zap, Sparkles, Users } from 'lucide-react'
import { useQuickInvitations } from '../hooks/useInvitations'
import type { TicketClass } from '../types'

interface EventOption {
  id: string
  title: string
}

interface Props {
  isOpen: boolean
  onClose: () => void
  eventId?: string
  events?: EventOption[]
}

export function QuickInviteDialog({ isOpen, onClose, eventId, events }: Props) {
  const [selectedEvent, setSelectedEvent] = useState(eventId || '')
  const [mode, setMode] = useState<'count' | 'names'>('count')
  const [count, setCount] = useState(10)
  const [names, setNames] = useState('')
  const [ticketClass, setTicketClass] = useState<TicketClass>('normal')
  const [requireRsvp, setRequireRsvp] = useState(false)
  const { mutate, isPending, data, isSuccess } = useQuickInvitations()

  if (!isOpen) return null

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedEvent) return
    const payload: any = { event_id: selectedEvent, ticket_class: ticketClass, require_rsvp: requireRsvp }
    if (mode === 'count') {
      payload.count = count
    } else {
      payload.names = names.split('\n').map((n) => n.trim()).filter(Boolean)
    }
    mutate(payload)
  }

  return (
    <div className="dialog-overlay" onClick={onClose}>
      <div className="dialog-panel dialog-panel--md" onClick={(e) => e.stopPropagation()}>
        <div className="dialog-header">
          <div className="dialog-header__title">
            <Zap size={20} />
            <span>دعوات سريعة</span>
          </div>
          <button className="dialog-close" onClick={onClose}><X size={18} /></button>
        </div>

        {isSuccess && data ? (
          <div className="dialog-body">
            <div className="inv-success-box">
              <div className="inv-success-box__icon">✅</div>
              <h3>تم إنشاء {data.created} دعوة بنجاح!</h3>
              <p>يمكنك الآن إرسالها للضيوف أو توليد ملفات الطباعة.</p>
              <button className="btn btn-primary" onClick={onClose}>إغلاق</button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="dialog-body">
            {/* Event Selector (if not pre-selected) */}
            {!eventId && events && events.length > 0 && (
              <div className="dialog-field">
                <label>الحدث *</label>
                <select
                  value={selectedEvent}
                  onChange={(e) => setSelectedEvent(e.target.value)}
                  required
                >
                  <option value="">اختر الحدث</option>
                  {events.map((ev) => (
                    <option key={ev.id} value={ev.id}>{ev.title}</option>
                  ))}
                </select>
              </div>
            )}

            {/* Ticket Class */}
            <div className="inv-class-picker">
              <button
                type="button"
                className={`inv-class-opt ${ticketClass === 'vip' ? 'inv-class-opt--active inv-class-opt--vip' : ''}`}
                onClick={() => setTicketClass('vip')}
              >
                <Sparkles size={16} /> VIP
              </button>
              <button
                type="button"
                className={`inv-class-opt ${ticketClass === 'normal' ? 'inv-class-opt--active' : ''}`}
                onClick={() => setTicketClass('normal')}
              >
                <Users size={16} /> عادي
              </button>
            </div>

            {/* Mode Toggle */}
            <div className="inv-mode-toggle">
              <button
                type="button"
                className={`inv-mode-btn ${mode === 'count' ? 'inv-mode-btn--active' : ''}`}
                onClick={() => setMode('count')}
              >
                بالعدد
              </button>
              <button
                type="button"
                className={`inv-mode-btn ${mode === 'names' ? 'inv-mode-btn--active' : ''}`}
                onClick={() => setMode('names')}
              >
                بالأسماء
              </button>
            </div>

            {mode === 'count' ? (
              <div className="dialog-field">
                <label>عدد الدعوات</label>
                <input
                  type="number" min={1} max={10000} value={count}
                  onChange={(e) => setCount(parseInt(e.target.value) || 1)}
                />
                <span className="dialog-hint">سيتم إنشاء {count} دعوة بدون أسماء</span>
              </div>
            ) : (
              <div className="dialog-field">
                <label>أسماء الضيوف (اسم واحد في كل سطر)</label>
                <textarea
                  rows={6} placeholder={"أحمد محمد\nفاطمة علي\nخالد سعيد"}
                  value={names}
                  onChange={(e) => setNames(e.target.value)}
                />
                <span className="dialog-hint">
                  {names.split('\n').filter((n) => n.trim()).length} اسم
                </span>
              </div>
            )}

            {/* RSVP Toggle */}
            <div className="dialog-field" style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 12 }}>
              <input
                type="checkbox"
                id="quickRequireRsvp"
                checked={requireRsvp}
                onChange={(e) => setRequireRsvp(e.target.checked)}
                style={{ width: '16px', height: '16px', accentColor: '#C9A96E' }}
              />
              <label htmlFor="quickRequireRsvp" style={{ margin: 0, fontSize: '0.85rem', color: '#d1d5db', cursor: 'pointer' }}>
                طلب تأكيد الحضور (RSVP) من الضيوف قبل إصدار الكود
              </label>
            </div>

            <div className="dialog-actions">
              <button type="button" className="btn btn-ghost" onClick={onClose}>إلغاء</button>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={isPending || !selectedEvent}
              >
                {isPending ? 'جاري الإنشاء...' : 'إنشاء الدعوات'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
