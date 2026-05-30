import { Guest } from '../types'
import { User, Phone, Mail, Building2, Edit2, Trash2 } from 'lucide-react'

interface Props {
  guest: Guest
  onEdit?: (guest: Guest) => void
  onDelete?: (id: string) => void
}

export function GuestCard({ guest, onEdit, onDelete }: Props) {
  return (
    <div className="guest-card">
      <div className="guest-card__avatar">
        <User size={20} />
      </div>
      <div className="guest-card__info">
        <div className="guest-card__name">
          {guest.full_name}
          {guest.full_name_ar && guest.full_name_ar !== guest.full_name && (
            <span className="guest-card__name-ar"> — {guest.full_name_ar}</span>
          )}
        </div>
        <div className="guest-card__meta">
          {guest.phone && (
            <span><Phone size={12} /> {guest.phone}</span>
          )}
          {guest.email && (
            <span><Mail size={12} /> {guest.email}</span>
          )}
          {guest.company && (
            <span><Building2 size={12} /> {guest.company}</span>
          )}
        </div>
      </div>
      <div className="guest-card__actions">
        <button className="inv-icon-btn" title="تعديل" onClick={() => onEdit?.(guest)}>
          <Edit2 size={14} />
        </button>
        <button
          className="inv-icon-btn"
          title="حذف"
          onClick={() => {
            if (confirm('هل تريد حذف هذا الضيف؟')) onDelete?.(guest.id)
          }}
        >
          <Trash2 size={14} />
        </button>
      </div>
    </div>
  )
}
