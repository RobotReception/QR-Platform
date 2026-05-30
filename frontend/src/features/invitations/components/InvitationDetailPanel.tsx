import { X, QrCode, User, Phone, Mail, MapPin, Sparkles, Copy, ExternalLink } from 'lucide-react'
import { Invitation, STATUS_LABELS, STATUS_COLORS } from '../types'

interface Props {
  invitation: Invitation | null
  onClose: () => void
}

export function InvitationDetailPanel({ invitation: inv, onClose }: Props) {
  if (!inv) return null

  const statusColor = STATUS_COLORS[inv.status] || '#64748b'
  const isVip = inv.ticket_class === 'vip'
  const publicUrl = `${window.location.origin}/i/${inv.token}`

  const copyLink = () => {
    navigator.clipboard.writeText(publicUrl)
  }

  return (
    <div className="inv-detail-overlay" onClick={onClose}>
      <aside className="inv-detail-panel" onClick={(e) => e.stopPropagation()}>
        <div className="inv-detail-header">
          <h2>تفاصيل الدعوة</h2>
          <button className="dialog-close" onClick={onClose}><X size={18} /></button>
        </div>

        {/* QR Code */}
        <div className="inv-detail-qr">
          {inv.barcode_png_url ? (
            <img src={inv.barcode_png_url} alt="QR Code" />
          ) : (
            <div className="inv-detail-qr__placeholder">
              <QrCode size={48} />
              <span>لم يتم التوليد بعد</span>
            </div>
          )}
        </div>

        {/* Status + Token */}
        <div className="inv-detail-status-row">
          <span
            className="inv-detail-status-badge"
            style={{ background: statusColor + '20', color: statusColor, borderColor: statusColor + '40' }}
          >
            {STATUS_LABELS[inv.status]}
          </span>
          <span className={`inv-detail-class ${isVip ? 'inv-detail-class--vip' : ''}`}>
            {isVip && <Sparkles size={12} />}
            {isVip ? 'VIP' : 'عادي'}
          </span>
        </div>

        {/* Public Link */}
        <div className="inv-detail-link-box">
          <span className="inv-detail-link-url">{publicUrl.slice(0, 40)}...</span>
          <button className="inv-icon-btn" onClick={copyLink} title="نسخ الرابط"><Copy size={14} /></button>
          <a href={publicUrl} target="_blank" rel="noopener noreferrer" className="inv-icon-btn" title="فتح"><ExternalLink size={14} /></a>
        </div>

        {/* Guest Info */}
        <div className="inv-detail-section">
          <h4>بيانات الضيف</h4>
          <div className="inv-detail-grid">
            {inv.guest_name && (
              <div className="inv-detail-item">
                <User size={14} /> <span>{inv.guest_name}</span>
              </div>
            )}
            {inv.guest_name_ar && inv.guest_name_ar !== inv.guest_name && (
              <div className="inv-detail-item">
                <User size={14} /> <span>{inv.guest_name_ar}</span>
              </div>
            )}
            {inv.guest_phone && (
              <div className="inv-detail-item">
                <Phone size={14} /> <span dir="ltr">{inv.guest_phone}</span>
              </div>
            )}
            {inv.guest_email && (
              <div className="inv-detail-item">
                <Mail size={14} /> <span dir="ltr">{inv.guest_email}</span>
              </div>
            )}
          </div>
        </div>

        {/* Seating */}
        {(inv.seat_number || inv.table_number || inv.hall || inv.zone) && (
          <div className="inv-detail-section">
            <h4>معلومات الجلوس</h4>
            <div className="inv-detail-grid">
              {inv.seat_number && (
                <div className="inv-detail-item"><MapPin size={14} /> <span>مقعد: {inv.seat_number}</span></div>
              )}
              {inv.table_number && (
                <div className="inv-detail-item"><MapPin size={14} /> <span>طاولة: {inv.table_number}</span></div>
              )}
              {inv.hall && (
                <div className="inv-detail-item"><MapPin size={14} /> <span>قاعة: {inv.hall}</span></div>
              )}
              {inv.zone && (
                <div className="inv-detail-item"><MapPin size={14} /> <span>منطقة: {inv.zone}</span></div>
              )}
            </div>
          </div>
        )}

        {/* RSVP */}
        {inv.rsvp_status && (
          <div className="inv-detail-section">
            <h4>حالة الرد (RSVP)</h4>
            <div className="inv-detail-rsvp">
              <span className={`inv-rsvp-badge inv-rsvp-badge--${inv.rsvp_status}`}>
                {inv.rsvp_status === 'accepted' ? 'قبول' : inv.rsvp_status === 'declined' ? 'اعتذار' : inv.rsvp_status}
              </span>
              {inv.plus_one_count > 0 && <span>+ {inv.plus_one_count} مرافق</span>}
            </div>
          </div>
        )}

        {/* Timeline */}
        <div className="inv-detail-section">
          <h4>الجدول الزمني</h4>
          <div className="inv-timeline">
            <div className="inv-timeline-item inv-timeline-item--done">
              <div className="inv-timeline-dot" />
              <div>
                <span>تم الإنشاء</span>
                <time>{new Date(inv.created_at).toLocaleString('ar')}</time>
              </div>
            </div>
            {inv.checked_in_at && (
              <div className="inv-timeline-item inv-timeline-item--done">
                <div className="inv-timeline-dot" />
                <div>
                  <span>تسجيل حضور</span>
                  <time>{new Date(inv.checked_in_at).toLocaleString('ar')}</time>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Notes */}
        {inv.notes && (
          <div className="inv-detail-section">
            <h4>ملاحظات</h4>
            <p className="inv-detail-notes">{inv.notes}</p>
          </div>
        )}
      </aside>
    </div>
  )
}
