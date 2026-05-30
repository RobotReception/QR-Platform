import { Invitation, STATUS_LABELS, STATUS_COLORS } from '../types'
import { QrCode, Sparkles, Ban, Eye } from 'lucide-react'

interface Props {
  invitation: Invitation
  selected?: boolean
  onSelect?: (id: string) => void
  onView?: (inv: Invitation) => void
  onRevoke?: (id: string) => void
}

export function InvitationCard({ invitation: inv, selected, onSelect, onView, onRevoke }: Props) {
  const statusColor = STATUS_COLORS[inv.status] || '#64748b'
  const statusLabel = STATUS_LABELS[inv.status] || inv.status
  const isVip = inv.ticket_class === 'vip'

  return (
    <div
      className={`inv-list-card ${selected ? 'inv-list-card--selected' : ''}`}
      onClick={() => onView?.(inv)}
      role="button"
      tabIndex={0}
    >
      {/* Selection checkbox */}
      {onSelect && (
        <label className="inv-list-card__check" onClick={(e) => e.stopPropagation()}>
          <input
            type="checkbox"
            checked={selected}
            onChange={() => onSelect(inv.id)}
          />
        </label>
      )}

      {/* QR preview */}
      <div className="inv-list-card__qr">
        {inv.barcode_png_url ? (
          <img src={inv.barcode_png_url} alt="QR" loading="lazy" />
        ) : (
          <QrCode size={32} style={{ opacity: 0.3 }} />
        )}
      </div>

      {/* Info */}
      <div className="inv-list-card__info">
        <div className="inv-list-card__name">
          {isVip && <Sparkles size={14} className="inv-vip-icon" />}
          {inv.guest_name || inv.guest_name_ar || 'بدون اسم'}
        </div>
        <div className="inv-list-card__meta">
          {inv.guest_phone && <span>{inv.guest_phone}</span>}
          {inv.seat_number && <span>مقعد: {inv.seat_number}</span>}
          <span className="inv-list-card__token">#{inv.token?.slice(0, 8)}</span>
        </div>
      </div>

      {/* Ticket class badge */}
      <span className={`inv-badge inv-badge--${inv.ticket_class}`}>
        {isVip ? 'VIP' : 'عادي'}
      </span>

      {/* Status badge */}
      <span className="inv-badge" style={{ background: statusColor + '20', color: statusColor }}>
        {statusLabel}
      </span>

      {/* Actions */}
      <div className="inv-list-card__actions" onClick={(e) => e.stopPropagation()}>
        <button className="inv-icon-btn" title="عرض" onClick={() => onView?.(inv)}>
          <Eye size={16} />
        </button>
        {inv.status === 'created' && (
          <button className="inv-icon-btn" title="إلغاء" onClick={() => onRevoke?.(inv.id)}>
            <Ban size={16} />
          </button>
        )}
      </div>
    </div>
  )
}
