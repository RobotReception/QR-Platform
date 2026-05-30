import { useState } from 'react'
import { X, Send, Link, Mail, MessageSquare, Smartphone } from 'lucide-react'
import { useSendInvitations } from '../hooks/useInvitations'
import type { DeliveryChannel } from '../types'

interface Props {
  isOpen: boolean
  onClose: () => void
  selectedIds: string[]
}

const CHANNELS: { value: DeliveryChannel; label: string; icon: any; available: boolean }[] = [
  { value: 'link', label: 'رابط مباشر', icon: Link, available: true },
  { value: 'email', label: 'بريد إلكتروني', icon: Mail, available: true },
  { value: 'sms', label: 'رسالة نصية SMS', icon: Smartphone, available: false },
  { value: 'whatsapp', label: 'واتساب', icon: MessageSquare, available: false },
]

export function SendInvitationsDialog({ isOpen, onClose, selectedIds }: Props) {
  const [channel, setChannel] = useState<DeliveryChannel>('link')
  const [message, setMessage] = useState('')
  const { mutate, isPending, data, isSuccess } = useSendInvitations()

  if (!isOpen) return null

  const handleSend = () => {
    mutate({
      invitation_ids: selectedIds,
      channel,
      message: message || undefined,
    })
  }

  return (
    <div className="dialog-overlay" onClick={onClose}>
      <div className="dialog-panel dialog-panel--md" onClick={(e) => e.stopPropagation()}>
        <div className="dialog-header">
          <div className="dialog-header__title">
            <Send size={20} />
            <span>إرسال الدعوات ({selectedIds.length})</span>
          </div>
          <button className="dialog-close" onClick={onClose}><X size={18} /></button>
        </div>

        {isSuccess && data ? (
          <div className="dialog-body">
            <div className="inv-success-box">
              <div className="inv-success-box__icon">📨</div>
              <h3>تم إرسال {data.sent} دعوة بنجاح!</h3>
              <button className="btn btn-primary" onClick={onClose}>إغلاق</button>
            </div>
          </div>
        ) : (
          <div className="dialog-body">
            <p className="dialog-desc">اختر طريقة إرسال الدعوات للضيوف</p>

            <div className="inv-channel-grid">
              {CHANNELS.map((ch) => (
                <button
                  key={ch.value}
                  className={`inv-channel-card ${channel === ch.value ? 'inv-channel-card--active' : ''} ${!ch.available ? 'inv-channel-card--disabled' : ''}`}
                  onClick={() => ch.available && setChannel(ch.value)}
                  disabled={!ch.available}
                >
                  <ch.icon size={24} />
                  <span>{ch.label}</span>
                  {!ch.available && <span className="inv-channel-soon">قريباً</span>}
                </button>
              ))}
            </div>

            <div className="dialog-field">
              <label>رسالة مرفقة (اختياري)</label>
              <textarea
                rows={3}
                placeholder="نتشرف بدعوتكم لحضور..."
                value={message}
                onChange={(e) => setMessage(e.target.value)}
              />
            </div>

            <div className="dialog-actions">
              <button className="btn btn-ghost" onClick={onClose}>إلغاء</button>
              <button className="btn btn-primary" onClick={handleSend} disabled={isPending}>
                <Send size={16} />
                {isPending ? 'جاري الإرسال...' : 'إرسال'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
