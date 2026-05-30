import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, DoorOpen, AlertCircle, Loader2, CheckSquare, Square } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { eventsAPI } from '../api/eventsApi'
import type { EventGateCreate, TicketClass } from '../types'

const schema = z.object({
  name: z.string().min(2, 'الاسم يجب أن يكون حرفين على الأقل'),
})

type FormData = z.infer<typeof schema>

interface Props {
  eventId: string
  isOpen: boolean
  onClose: () => void
}

export function CreateGateDialog({ eventId, isOpen, onClose }: Props) {
  const queryClient = useQueryClient()
  const [serverError, setServerError] = useState('')
  const [allowedClasses, setAllowedClasses] = useState<TicketClass[]>(['normal', 'vip'])

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  const createMutation = useMutation({
    mutationFn: (data: EventGateCreate) => eventsAPI.createGate(eventId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['events-gates', eventId] })
      reset()
      onClose()
    },
    onError: (err: any) => {
      setServerError(err?.response?.data?.detail || 'حدث خطأ غير متوقع')
    }
  })

  const toggleClass = (tc: TicketClass) => {
    setAllowedClasses(prev => 
      prev.includes(tc) ? prev.filter(c => c !== tc) : [...prev, tc]
    )
  }

  const onSubmit = (data: FormData) => {
    if (allowedClasses.length === 0) {
      setServerError('يجب تحديد فئة تذاكر واحدة على الأقل')
      return
    }
    setServerError('')
    createMutation.mutate({
      name: data.name,
      allowed_classes: allowedClasses,
    })
  }

  if (!isOpen) return null

  return (
    <AnimatePresence>
      <div className="dialog-overlay" onClick={onClose}>
        <motion.div
          className="dialog-content"
          initial={{ opacity: 0, scale: 0.95, y: 10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 10 }}
          onClick={e => e.stopPropagation()}
        >
          <div className="dialog-header">
            <h3>إنشاء بوابة دخول</h3>
            <button className="dialog-close" onClick={onClose}>
              <X size={20} />
            </button>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="dialog-form" noValidate>
            {serverError && (
              <div className="auth-error" style={{ marginBottom: 16 }}>
                <AlertCircle size={16} />
                <span>{serverError}</span>
              </div>
            )}

            <div className="form-field">
              <label>اسم البوابة</label>
              <input
                {...register('name')}
                type="text"
                placeholder="مثال: البوابة الشرقية (VIP)"
                className={errors.name ? 'error' : ''}
              />
              {errors.name && <span className="form-error">{errors.name.message}</span>}
            </div>

            <div className="form-field">
              <label>الفئات المسموح لها بالدخول</label>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 8 }}>
                <label className="toggle-row" style={{ cursor: 'pointer', padding: '12px 16px', margin: 0 }}>
                  <div className="toggle-row-info">
                    <h4 style={{ color: '#c9a96e' }}>كبار الشخصيات (VIP)</h4>
                    <p>أصحاب تذاكر ودعوات الـ VIP فقط</p>
                  </div>
                  <button type="button" className="checkbox-btn" onClick={() => toggleClass('vip')}>
                    {allowedClasses.includes('vip') ? <CheckSquare size={20} color="#c9a96e" /> : <Square size={20} />}
                  </button>
                </label>
                
                <label className="toggle-row" style={{ cursor: 'pointer', padding: '12px 16px', margin: 0 }}>
                  <div className="toggle-row-info">
                    <h4>الضيوف العاديين (Normal)</h4>
                    <p>التذاكر العادية المخصصة للجمهور</p>
                  </div>
                  <button type="button" className="checkbox-btn" onClick={() => toggleClass('normal')}>
                    {allowedClasses.includes('normal') ? <CheckSquare size={20} /> : <Square size={20} />}
                  </button>
                </label>
              </div>
            </div>

            <div className="dialog-actions" style={{ marginTop: 24 }}>
              <button type="button" className="btn btn-ghost" onClick={onClose} disabled={isSubmitting}>
                إلغاء
              </button>
              <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
                {isSubmitting ? <><Loader2 size={16} className="spin" /> جاري الحفظ</> : <><DoorOpen size={16} /> إضافة البوابة</>}
              </button>
            </div>
          </form>
        </motion.div>
      </div>
    </AnimatePresence>
  )
}
