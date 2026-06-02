import { useState } from 'react'
import { X, Ticket, Sparkles, Users } from 'lucide-react'
import { useCreateInvitation } from '../hooks/useInvitations'
import type { InvitationCreateRequest } from '../types'

interface EventOption {
  id: string
  title: string
}

interface Props {
  isOpen: boolean
  onClose: () => void
  eventId?: string
  eventTitle?: string
  events?: EventOption[]
}

export function CreateInvitationDialog({ isOpen, onClose, eventId, eventTitle, events }: Props) {
  const [selectedEvent, setSelectedEvent] = useState(eventId || '')
  const [form, setForm] = useState<InvitationCreateRequest>({
    event_id: eventId || '',
    ticket_class: 'normal',
  })
  const { mutate, isPending } = useCreateInvitation()

  if (!isOpen) return null

  const update = (patch: Partial<InvitationCreateRequest>) =>
    setForm((p) => ({ ...p, ...patch }))

  const handleEventChange = (eid: string) => {
    setSelectedEvent(eid)
    update({ event_id: eid })
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.event_id) return
    mutate({ ...form, event_id: form.event_id }, { onSuccess: () => onClose() })
  }

  const resolvedTitle = eventTitle || events?.find((e) => e.id === selectedEvent)?.title

  return (
    <div className="dialog-overlay" onClick={onClose}>
      <div className="dialog-panel dialog-panel--md" onClick={(e) => e.stopPropagation()}>
        <div className="dialog-header">
          <div className="dialog-header__title">
            <Ticket size={20} />
            <span>إنشاء دعوة جديدة</span>
          </div>
          <button className="dialog-close" onClick={onClose}><X size={18} /></button>
        </div>

        {/* Event Selector */}
        {!eventId && events && events.length > 0 && (
          <div className="dialog-body" style={{ paddingBottom: 0 }}>
            <div className="dialog-field">
              <label>الحدث *</label>
              <select
                value={selectedEvent}
                onChange={(e) => handleEventChange(e.target.value)}
                required
              >
                <option value="">اختر الحدث</option>
                {events.map((ev) => (
                  <option key={ev.id} value={ev.id}>{ev.title}</option>
                ))}
              </select>
            </div>
          </div>
        )}

        {resolvedTitle && (
          <div className="dialog-event-tag">الحدث: {resolvedTitle}</div>
        )}

        <form onSubmit={handleSubmit} className="dialog-body">
          {/* Ticket Class */}
          <div className="inv-class-picker">
            <button
              type="button"
              className={`inv-class-opt ${form.ticket_class === 'vip' ? 'inv-class-opt--active inv-class-opt--vip' : ''}`}
              onClick={() => update({ ticket_class: 'vip' })}
            >
              <Sparkles size={16} /> VIP
            </button>
            <button
              type="button"
              className={`inv-class-opt ${form.ticket_class === 'normal' ? 'inv-class-opt--active' : ''}`}
              onClick={() => update({ ticket_class: 'normal' })}
            >
              <Users size={16} /> عادي
            </button>
          </div>

          {/* Guest Info */}
          <div className="dialog-grid-2">
            <div className="dialog-field">
              <label>اسم الضيف</label>
              <input
                type="text" placeholder="أحمد محمد"
                value={form.guest_name || ''}
                onChange={(e) => update({ guest_name: e.target.value })}
              />
            </div>
            <div className="dialog-field">
              <label>الاسم بالعربي</label>
              <input
                type="text" placeholder="أحمد محمد"
                value={form.guest_name_ar || ''}
                onChange={(e) => update({ guest_name_ar: e.target.value })}
              />
            </div>
          </div>

          <div className="dialog-grid-2">
            <div className="dialog-field">
              <label>رقم الهاتف</label>
              <input
                type="tel" placeholder="+967 xxx xxx xxx" dir="ltr"
                value={form.guest_phone || ''}
                onChange={(e) => update({ guest_phone: e.target.value })}
              />
            </div>
            <div className="dialog-field">
              <label>البريد الإلكتروني</label>
              <input
                type="email" placeholder="email@example.com" dir="ltr"
                value={form.guest_email || ''}
                onChange={(e) => update({ guest_email: e.target.value })}
              />
            </div>
          </div>

          {/* Seating */}
          <div className="dialog-grid-3">
            <div className="dialog-field">
              <label>رقم المقعد</label>
              <input
                type="text" placeholder="A12"
                value={form.seat_number || ''}
                onChange={(e) => update({ seat_number: e.target.value })}
              />
            </div>
            <div className="dialog-field">
              <label>رقم الطاولة</label>
              <input
                type="text" placeholder="5"
                value={form.table_number || ''}
                onChange={(e) => update({ table_number: e.target.value })}
              />
            </div>
            <div className="dialog-field">
              <label>القاعة</label>
              <input
                type="text" placeholder="القاعة الرئيسية"
                value={form.hall || ''}
                onChange={(e) => update({ hall: e.target.value })}
              />
            </div>
          </div>

          {/* RSVP Toggle */}
          <div className="dialog-field" style={{ display: 'flex', alignItems: 'center', gap: 8, margin: '12px 0' }}>
            <input
              type="checkbox"
              id="singleRequireRsvp"
              checked={form.require_rsvp || false}
              onChange={(e) => update({ require_rsvp: e.target.checked })}
              style={{ width: '16px', height: '16px', accentColor: '#C9A96E' }}
            />
            <label htmlFor="singleRequireRsvp" style={{ margin: 0, fontSize: '0.85rem', color: '#d1d5db', cursor: 'pointer' }}>
              طلب تأكيد الحضور (RSVP) من الضيف قبل إصدار الكود
            </label>
          </div>

          {/* Notes */}
          <div className="dialog-field">
            <label>ملاحظات</label>
            <textarea
              rows={2} placeholder="أي ملاحظات إضافية..."
              value={form.notes || ''}
              onChange={(e) => update({ notes: e.target.value })}
            />
          </div>

          {/* Actions */}
          <div className="dialog-actions">
            <button type="button" className="btn btn-ghost" onClick={onClose}>إلغاء</button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={isPending || !form.event_id}
            >
              {isPending ? 'جاري الإنشاء...' : 'إنشاء الدعوة'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
