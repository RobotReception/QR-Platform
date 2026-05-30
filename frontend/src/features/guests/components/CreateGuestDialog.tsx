import { useState } from 'react'
import { X, UserPlus } from 'lucide-react'
import { useCreateGuest, useUpdateGuest } from '../hooks/useGuests'
import type { Guest, GuestCreateRequest } from '../types'

interface Props {
  isOpen: boolean
  onClose: () => void
  editGuest?: Guest | null
}

export function CreateGuestDialog({ isOpen, onClose, editGuest }: Props) {
  const [form, setForm] = useState<GuestCreateRequest>({
    full_name: editGuest?.full_name || '',
    full_name_ar: editGuest?.full_name_ar || '',
    phone: editGuest?.phone || '',
    email: editGuest?.email || '',
    company: editGuest?.company || '',
    title: editGuest?.title || '',
    notes: editGuest?.notes || '',
  })

  const createMutation = useCreateGuest()
  const updateMutation = useUpdateGuest()
  const isPending = createMutation.isPending || updateMutation.isPending

  if (!isOpen) return null

  const update = (patch: Partial<GuestCreateRequest>) =>
    setForm((p) => ({ ...p, ...patch }))

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.full_name.trim()) return

    if (editGuest) {
      updateMutation.mutate({ id: editGuest.id, data: form }, { onSuccess: onClose })
    } else {
      createMutation.mutate(form, { onSuccess: onClose })
    }
  }

  return (
    <div className="dialog-overlay" onClick={onClose}>
      <div className="dialog-panel dialog-panel--md" onClick={(e) => e.stopPropagation()}>
        <div className="dialog-header">
          <div className="dialog-header__title">
            <UserPlus size={20} />
            <span>{editGuest ? 'تعديل ضيف' : 'إضافة ضيف جديد'}</span>
          </div>
          <button className="dialog-close" onClick={onClose}><X size={18} /></button>
        </div>

        <form onSubmit={handleSubmit} className="dialog-body">
          <div className="dialog-grid-2">
            <div className="dialog-field">
              <label>الاسم الكامل *</label>
              <input
                type="text" required placeholder="أحمد محمد"
                value={form.full_name}
                onChange={(e) => update({ full_name: e.target.value })}
              />
            </div>
            <div className="dialog-field">
              <label>الاسم بالعربي</label>
              <input
                type="text" placeholder="أحمد محمد"
                value={form.full_name_ar || ''}
                onChange={(e) => update({ full_name_ar: e.target.value })}
              />
            </div>
          </div>

          <div className="dialog-grid-2">
            <div className="dialog-field">
              <label>رقم الهاتف</label>
              <input
                type="tel" placeholder="+967 xxx xxx xxx" dir="ltr"
                value={form.phone || ''}
                onChange={(e) => update({ phone: e.target.value })}
              />
            </div>
            <div className="dialog-field">
              <label>البريد الإلكتروني</label>
              <input
                type="email" placeholder="email@example.com" dir="ltr"
                value={form.email || ''}
                onChange={(e) => update({ email: e.target.value })}
              />
            </div>
          </div>

          <div className="dialog-grid-2">
            <div className="dialog-field">
              <label>الشركة / المؤسسة</label>
              <input
                type="text" placeholder="شركة المستقبل"
                value={form.company || ''}
                onChange={(e) => update({ company: e.target.value })}
              />
            </div>
            <div className="dialog-field">
              <label>المسمى الوظيفي</label>
              <input
                type="text" placeholder="مدير عام"
                value={form.title || ''}
                onChange={(e) => update({ title: e.target.value })}
              />
            </div>
          </div>

          <div className="dialog-field">
            <label>ملاحظات</label>
            <textarea
              rows={2} placeholder="أي ملاحظات إضافية..."
              value={form.notes || ''}
              onChange={(e) => update({ notes: e.target.value })}
            />
          </div>

          <div className="dialog-actions">
            <button type="button" className="btn btn-ghost" onClick={onClose}>إلغاء</button>
            <button type="submit" className="btn btn-primary" disabled={isPending || !form.full_name.trim()}>
              {isPending ? 'جاري الحفظ...' : editGuest ? 'حفظ التعديلات' : 'إضافة الضيف'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
