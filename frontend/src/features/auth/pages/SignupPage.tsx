import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { motion } from 'framer-motion'
import { Eye, EyeOff, UserPlus, Loader2, AlertCircle, CheckCircle2, Building2, Users, Clock } from 'lucide-react'
import { authAPI } from '../api/authApi'
import './auth.css'

type Mode = 'personal' | 'organizer'

/* ── Personal (instant) signup ── */
const personalSchema = z.object({
  full_name:         z.string().min(2, 'الاسم يجب أن يكون حرفين على الأقل'),
  organization_name: z.string().min(2, 'اسم المؤسسة يجب أن يكون حرفين على الأقل'),
  email:             z.string().email('بريد إلكتروني غير صالح'),
  password:          z.string()
    .min(8, 'كلمة المرور يجب أن تكون 8 أحرف على الأقل')
    .regex(/[A-Z]/, 'يجب أن تحتوي على حرف كبير')
    .regex(/[0-9]/, 'يجب أن تحتوي على رقم'),
  confirm_password: z.string(),
}).refine(d => d.password === d.confirm_password, {
  message: 'كلمات المرور غير متطابقة',
  path: ['confirm_password'],
})
type PersonalForm = z.infer<typeof personalSchema>

/* ── Organizer-team request (awaits approval) ── */
const organizerSchema = z.object({
  full_name:   z.string().min(2, 'الاسم يجب أن يكون حرفين على الأقل'),
  email:       z.string().email('بريد إلكتروني غير صالح'),
  password:    z.string()
    .min(8, 'كلمة المرور يجب أن تكون 8 أحرف على الأقل')
    .regex(/[A-Z]/, 'يجب أن تحتوي على حرف كبير')
    .regex(/[0-9]/, 'يجب أن تحتوي على رقم'),
  confirm_password: z.string(),
  phone:       z.string().optional(),
  org_name:    z.string().min(2, 'اسم الفريق/المؤسسة مطلوب'),
  org_type:    z.string().optional(),
  description: z.string().optional(),
  city:        z.string().optional(),
  country:     z.string().optional(),
  website:     z.string().url('رابط غير صالح').optional().or(z.literal('')),
  contact_handle: z.string().optional(),
  expected_events_per_month: z.coerce.number().int().min(0).optional(),
  expected_attendees:        z.coerce.number().int().min(0).optional(),
  proof_url:   z.string().url('رابط الإثبات غير صالح').min(1, 'إثبات أنك فريق تنظيم مطلوب'),
  documents_url: z.string().url('رابط غير صالح').optional().or(z.literal('')),
  notes:       z.string().optional(),
}).refine(d => d.password === d.confirm_password, {
  message: 'كلمات المرور غير متطابقة',
  path: ['confirm_password'],
})
type OrganizerForm = z.infer<typeof organizerSchema>

const passwordRules = [
  { label: '8 أحرف على الأقل', test: (p: string) => p.length >= 8 },
  { label: 'حرف كبير (A-Z)',    test: (p: string) => /[A-Z]/.test(p) },
  { label: 'رقم (0-9)',         test: (p: string) => /[0-9]/.test(p) },
]

export default function SignupPage() {
  const navigate = useNavigate()
  const [mode, setMode] = useState<Mode>('personal')

  return (
    <div className="auth-page">
      <div className="auth-orb auth-orb--1" />
      <div className="auth-orb auth-orb--2" />

      <motion.div
        className="auth-card auth-card--wide"
        initial={{ opacity: 0, y: 24, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.5, ease: [0.34, 1.56, 0.64, 1] }}
      >
        <div className="auth-logo">
          <img src="/logo.png" alt="Qentry" className="auth-logo__img" />
        </div>

        <div className="auth-header">
          <h1 className="auth-title">إنشاء حساب جديد</h1>
          <p className="auth-subtitle">انضم إلى Qentry وابدأ رحلتك</p>
        </div>

        {/* Mode toggle */}
        <div className="auth-modes">
          <button
            type="button"
            className={`auth-mode ${mode === 'personal' ? 'auth-mode--active' : ''}`}
            onClick={() => setMode('personal')}
          >
            <UserPlus size={16} /> حساب عادي
          </button>
          <button
            type="button"
            className={`auth-mode ${mode === 'organizer' ? 'auth-mode--active' : ''}`}
            onClick={() => setMode('organizer')}
          >
            <Users size={16} /> فريق تنظيم
          </button>
        </div>

        {mode === 'personal'
          ? <PersonalSignup navigate={navigate} />
          : <OrganizerSignup />}

        <div className="auth-footer">
          <span>لديك حساب بالفعل؟</span>
          <Link to="/auth/login" className="auth-footer__link">تسجيل الدخول</Link>
        </div>
      </motion.div>
    </div>
  )
}

/* ══════════════════════════════════════════════════
   PERSONAL (instant)
   ══════════════════════════════════════════════════ */
function PersonalSignup({ navigate }: { navigate: ReturnType<typeof useNavigate> }) {
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirm, setShowConfirm]   = useState(false)
  const [serverError, setServerError]   = useState('')
  const [successMsg, setSuccessMsg]      = useState('')

  const { register, handleSubmit, watch, formState: { errors, isSubmitting } } =
    useForm<PersonalForm>({ resolver: zodResolver(personalSchema) })
  const passwordValue = watch('password', '')

  const onSubmit = async (data: PersonalForm) => {
    setServerError(''); setSuccessMsg('')
    try {
      const res = await authAPI.signup({
        email: data.email, password: data.password,
        full_name: data.full_name, organization_name: data.organization_name,
      })
      setSuccessMsg(res.message || 'تم إنشاء الحساب! تحقق من بريدك الإلكتروني.')
      setTimeout(() => navigate('/auth/login'), 3000)
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } }
      setServerError(e?.response?.data?.detail || 'حدث خطأ، حاول مرة أخرى')
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="auth-form" noValidate>
      {serverError && (
        <motion.div className="auth-error" initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}>
          <AlertCircle size={16} /><span>{serverError}</span>
        </motion.div>
      )}
      {successMsg && (
        <motion.div className="auth-success" initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}>
          <CheckCircle2 size={16} /><span>{successMsg}</span>
        </motion.div>
      )}

      <div className="auth-grid">
        <div className="field">
          <label className="field__label">الاسم الكامل</label>
          <input {...register('full_name')} type="text"
            className={`field__input ${errors.full_name ? 'field__input--error' : ''}`}
            placeholder="محمد العبدالله" />
          {errors.full_name && <span className="field__error">{errors.full_name.message}</span>}
        </div>
        <div className="field">
          <label className="field__label">اسم المؤسسة</label>
          <input {...register('organization_name')} type="text"
            className={`field__input ${errors.organization_name ? 'field__input--error' : ''}`}
            placeholder="شركة الأفق" />
          {errors.organization_name && <span className="field__error">{errors.organization_name.message}</span>}
        </div>
      </div>

      <div className="field">
        <label className="field__label">البريد الإلكتروني</label>
        <input {...register('email')} type="email"
          className={`field__input ${errors.email ? 'field__input--error' : ''}`}
          placeholder="you@company.com" dir="ltr" />
        {errors.email && <span className="field__error">{errors.email.message}</span>}
      </div>

      <div className="field">
        <label className="field__label">كلمة المرور</label>
        <div className="field__input-wrapper">
          <input {...register('password')} type={showPassword ? 'text' : 'password'}
            className={`field__input field__input--padded ${errors.password ? 'field__input--error' : ''}`}
            placeholder="••••••••" dir="ltr" />
          <button type="button" className="field__eye" onClick={() => setShowPassword(v => !v)} tabIndex={-1}>
            {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        </div>
        {passwordValue && (
          <div className="password-rules">
            {passwordRules.map(r => (
              <div key={r.label} className={`password-rule ${r.test(passwordValue) ? 'password-rule--ok' : ''}`}>
                <CheckCircle2 size={13} /><span>{r.label}</span>
              </div>
            ))}
          </div>
        )}
        {errors.password && <span className="field__error">{errors.password.message}</span>}
      </div>

      <div className="field">
        <label className="field__label">تأكيد كلمة المرور</label>
        <div className="field__input-wrapper">
          <input {...register('confirm_password')} type={showConfirm ? 'text' : 'password'}
            className={`field__input field__input--padded ${errors.confirm_password ? 'field__input--error' : ''}`}
            placeholder="••••••••" dir="ltr" />
          <button type="button" className="field__eye" onClick={() => setShowConfirm(v => !v)} tabIndex={-1}>
            {showConfirm ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        </div>
        {errors.confirm_password && <span className="field__error">{errors.confirm_password.message}</span>}
      </div>

      <button type="submit" className="auth-btn" disabled={isSubmitting}>
        {isSubmitting
          ? <><Loader2 size={18} className="spin" /> جاري إنشاء الحساب...</>
          : <><UserPlus size={18} /> إنشاء الحساب</>}
      </button>
    </form>
  )
}

/* ══════════════════════════════════════════════════
   ORGANIZER TEAM (request → platform approval)
   ══════════════════════════════════════════════════ */
function OrganizerSignup() {
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirm, setShowConfirm]   = useState(false)
  const [serverError, setServerError]   = useState('')
  const [submitted, setSubmitted]        = useState(false)

  const { register, handleSubmit, watch, formState: { errors, isSubmitting } } =
    useForm<OrganizerForm>({ resolver: zodResolver(organizerSchema) })
  const passwordValue = watch('password', '')

  const onSubmit = async (data: OrganizerForm) => {
    setServerError('')
    try {
      await authAPI.orgRequest({
        full_name: data.full_name, email: data.email, password: data.password,
        phone: data.phone || undefined,
        org_name: data.org_name, org_type: data.org_type || undefined,
        description: data.description || undefined,
        city: data.city || undefined, country: data.country || undefined,
        website: data.website || undefined, contact_handle: data.contact_handle || undefined,
        expected_events_per_month: data.expected_events_per_month,
        expected_attendees: data.expected_attendees,
        proof_url: data.proof_url, documents_url: data.documents_url || undefined,
        notes: data.notes || undefined,
      })
      setSubmitted(true)
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } }
      setServerError(e?.response?.data?.detail || 'حدث خطأ، حاول مرة أخرى')
    }
  }

  if (submitted) {
    return (
      <motion.div className="auth-pending" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
        <div className="auth-pending__icon"><Clock size={40} /></div>
        <h2 className="auth-pending__title">طلبك قيد المراجعة</h2>
        <p className="auth-pending__text">
          استلمنا طلب تسجيل فريق التنظيم الخاص بك. سيقوم فريق المنصة بمراجعته،
          وستصلك رسالة على بريدك الإلكتروني فور الموافقة لتتمكن من تسجيل الدخول.
        </p>
        <Link to="/auth/login" className="auth-btn auth-btn--inline">العودة لتسجيل الدخول</Link>
      </motion.div>
    )
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="auth-form" noValidate>
      <div className="auth-note">
        <Building2 size={16} />
        <span>تسجيل فريق التنظيم يتطلب موافقة إدارة المنصة. لن يتم إنشاء الحساب إلا بعد الموافقة.</span>
      </div>

      {serverError && (
        <motion.div className="auth-error" initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}>
          <AlertCircle size={16} /><span>{serverError}</span>
        </motion.div>
      )}

      <div className="auth-section-label">بيانات مقدّم الطلب</div>
      <div className="auth-grid">
        <div className="field">
          <label className="field__label">الاسم الكامل</label>
          <input {...register('full_name')} type="text"
            className={`field__input ${errors.full_name ? 'field__input--error' : ''}`}
            placeholder="محمد العبدالله" />
          {errors.full_name && <span className="field__error">{errors.full_name.message}</span>}
        </div>
        <div className="field">
          <label className="field__label">رقم الجوال</label>
          <input {...register('phone')} type="tel"
            className="field__input" placeholder="05xxxxxxxx" dir="ltr" />
        </div>
      </div>

      <div className="field">
        <label className="field__label">البريد الإلكتروني</label>
        <input {...register('email')} type="email"
          className={`field__input ${errors.email ? 'field__input--error' : ''}`}
          placeholder="you@company.com" dir="ltr" />
        {errors.email && <span className="field__error">{errors.email.message}</span>}
      </div>

      <div className="auth-grid">
        <div className="field">
          <label className="field__label">كلمة المرور</label>
          <div className="field__input-wrapper">
            <input {...register('password')} type={showPassword ? 'text' : 'password'}
              className={`field__input field__input--padded ${errors.password ? 'field__input--error' : ''}`}
              placeholder="••••••••" dir="ltr" />
            <button type="button" className="field__eye" onClick={() => setShowPassword(v => !v)} tabIndex={-1}>
              {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>
          {errors.password && <span className="field__error">{errors.password.message}</span>}
        </div>
        <div className="field">
          <label className="field__label">تأكيد كلمة المرور</label>
          <div className="field__input-wrapper">
            <input {...register('confirm_password')} type={showConfirm ? 'text' : 'password'}
              className={`field__input field__input--padded ${errors.confirm_password ? 'field__input--error' : ''}`}
              placeholder="••••••••" dir="ltr" />
            <button type="button" className="field__eye" onClick={() => setShowConfirm(v => !v)} tabIndex={-1}>
              {showConfirm ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>
          {errors.confirm_password && <span className="field__error">{errors.confirm_password.message}</span>}
        </div>
      </div>
      {passwordValue && (
        <div className="password-rules">
          {passwordRules.map(r => (
            <div key={r.label} className={`password-rule ${r.test(passwordValue) ? 'password-rule--ok' : ''}`}>
              <CheckCircle2 size={13} /><span>{r.label}</span>
            </div>
          ))}
        </div>
      )}

      <div className="auth-section-label">بيانات المؤسسة / الفريق</div>
      <div className="auth-grid">
        <div className="field">
          <label className="field__label">اسم الفريق / المؤسسة</label>
          <input {...register('org_name')} type="text"
            className={`field__input ${errors.org_name ? 'field__input--error' : ''}`}
            placeholder="فريق أفق للتنظيم" />
          {errors.org_name && <span className="field__error">{errors.org_name.message}</span>}
        </div>
        <div className="field">
          <label className="field__label">نوع النشاط</label>
          <input {...register('org_type')} type="text"
            className="field__input" placeholder="تنظيم فعاليات، مؤتمرات..." />
        </div>
      </div>

      <div className="field">
        <label className="field__label">وصف مختصر</label>
        <textarea {...register('description')} rows={2}
          className="field__input" placeholder="نبذة عن نشاط الفريق وخبراته" />
      </div>

      <div className="auth-grid">
        <div className="field">
          <label className="field__label">المدينة</label>
          <input {...register('city')} type="text" className="field__input" placeholder="الرياض" />
        </div>
        <div className="field">
          <label className="field__label">الدولة</label>
          <input {...register('country')} type="text" className="field__input" placeholder="السعودية" />
        </div>
      </div>

      <div className="auth-grid">
        <div className="field">
          <label className="field__label">الموقع الإلكتروني (اختياري)</label>
          <input {...register('website')} type="url"
            className={`field__input ${errors.website ? 'field__input--error' : ''}`}
            placeholder="https://..." dir="ltr" />
          {errors.website && <span className="field__error">{errors.website.message}</span>}
        </div>
        <div className="field">
          <label className="field__label">حساب التواصل (اختياري)</label>
          <input {...register('contact_handle')} type="text"
            className="field__input" placeholder="@account" dir="ltr" />
        </div>
      </div>

      <div className="auth-section-label">حجم النشاط المتوقع</div>
      <div className="auth-grid">
        <div className="field">
          <label className="field__label">عدد الفعاليات شهرياً</label>
          <input {...register('expected_events_per_month')} type="number" min={0}
            className="field__input" placeholder="5" dir="ltr" />
        </div>
        <div className="field">
          <label className="field__label">الحضور المتوقع للفعالية</label>
          <input {...register('expected_attendees')} type="number" min={0}
            className="field__input" placeholder="2000" dir="ltr" />
        </div>
      </div>

      <div className="auth-section-label">الإثبات والمستندات</div>
      <div className="field">
        <label className="field__label">رابط إثبات أنك فريق تنظيم</label>
        <input {...register('proof_url')} type="url"
          className={`field__input ${errors.proof_url ? 'field__input--error' : ''}`}
          placeholder="https://... (سجل تجاري، ترخيص، أعمال سابقة)" dir="ltr" />
        {errors.proof_url && <span className="field__error">{errors.proof_url.message}</span>}
      </div>
      <div className="field">
        <label className="field__label">رابط مستندات إضافية (اختياري)</label>
        <input {...register('documents_url')} type="url"
          className={`field__input ${errors.documents_url ? 'field__input--error' : ''}`}
          placeholder="https://..." dir="ltr" />
        {errors.documents_url && <span className="field__error">{errors.documents_url.message}</span>}
      </div>
      <div className="field">
        <label className="field__label">ملاحظات للإدارة (اختياري)</label>
        <textarea {...register('notes')} rows={2}
          className="field__input" placeholder="أي معلومات إضافية تساعد في مراجعة طلبك" />
      </div>

      <button type="submit" className="auth-btn" disabled={isSubmitting}>
        {isSubmitting
          ? <><Loader2 size={18} className="spin" /> جاري إرسال الطلب...</>
          : <><Users size={18} /> إرسال طلب التسجيل</>}
      </button>
    </form>
  )
}
