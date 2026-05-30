import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { motion } from 'framer-motion'
import { Eye, EyeOff, UserPlus, Loader2, AlertCircle, CheckCircle2 } from 'lucide-react'
import { authAPI } from '../api/authApi'
import './auth.css'

const schema = z.object({
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
type FormData = z.infer<typeof schema>

const passwordRules = [
  { label: '8 أحرف على الأقل',     test: (p: string) => p.length >= 8 },
  { label: 'حرف كبير (A-Z)',        test: (p: string) => /[A-Z]/.test(p) },
  { label: 'رقم (0-9)',             test: (p: string) => /[0-9]/.test(p) },
]

export default function SignupPage() {
  const navigate      = useNavigate()
  const [showPassword, setShowPassword]       = useState(false)
  const [showConfirm, setShowConfirm]         = useState(false)
  const [serverError, setServerError]         = useState('')
  const [successMsg, setSuccessMsg]           = useState('')

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) })

  const passwordValue = watch('password', '')

  const onSubmit = async (data: FormData) => {
    setServerError('')
    setSuccessMsg('')
    try {
      const res = await authAPI.signup({
        email:             data.email,
        password:          data.password,
        full_name:         data.full_name,
        organization_name: data.organization_name,
      })
      setSuccessMsg(res.message || 'تم إنشاء الحساب! تحقق من بريدك الإلكتروني.')
      setTimeout(() => navigate('/auth/login'), 3000)
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } }
      setServerError(e?.response?.data?.detail || 'حدث خطأ، حاول مرة أخرى')
    }
  }

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
        {/* Logo */}
        <div className="auth-logo">
          <img src="/logo.png" alt="Qentry" className="auth-logo__img" />
        </div>

        <div className="auth-header">
          <h1 className="auth-title">إنشاء حساب جديد</h1>
          <p className="auth-subtitle">انضم إلى Qentry وابدأ رحلتك</p>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="auth-form" noValidate>

          {/* Server Error */}
          {serverError && (
            <motion.div className="auth-error" initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}>
              <AlertCircle size={16} />
              <span>{serverError}</span>
            </motion.div>
          )}

          {/* Success */}
          {successMsg && (
            <motion.div className="auth-success" initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}>
              <CheckCircle2 size={16} />
              <span>{successMsg}</span>
            </motion.div>
          )}

          {/* Two columns */}
          <div className="auth-grid">
            {/* Full Name */}
            <div className="field">
              <label className="field__label">الاسم الكامل</label>
              <input
                {...register('full_name')}
                type="text"
                className={`field__input ${errors.full_name ? 'field__input--error' : ''}`}
                placeholder="محمد العبدالله"
              />
              {errors.full_name && <span className="field__error">{errors.full_name.message}</span>}
            </div>

            {/* Organization */}
            <div className="field">
              <label className="field__label">اسم المؤسسة</label>
              <input
                {...register('organization_name')}
                type="text"
                className={`field__input ${errors.organization_name ? 'field__input--error' : ''}`}
                placeholder="شركة الأفق"
              />
              {errors.organization_name && <span className="field__error">{errors.organization_name.message}</span>}
            </div>
          </div>

          {/* Email */}
          <div className="field">
            <label className="field__label">البريد الإلكتروني</label>
            <input
              {...register('email')}
              type="email"
              className={`field__input ${errors.email ? 'field__input--error' : ''}`}
              placeholder="you@company.com"
              dir="ltr"
            />
            {errors.email && <span className="field__error">{errors.email.message}</span>}
          </div>

          {/* Password */}
          <div className="field">
            <label className="field__label">كلمة المرور</label>
            <div className="field__input-wrapper">
              <input
                {...register('password')}
                type={showPassword ? 'text' : 'password'}
                className={`field__input field__input--padded ${errors.password ? 'field__input--error' : ''}`}
                placeholder="••••••••"
                dir="ltr"
              />
              <button type="button" className="field__eye" onClick={() => setShowPassword(v => !v)} tabIndex={-1}>
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
            {/* Password Strength */}
            {passwordValue && (
              <div className="password-rules">
                {passwordRules.map(r => (
                  <div key={r.label} className={`password-rule ${r.test(passwordValue) ? 'password-rule--ok' : ''}`}>
                    <CheckCircle2 size={13} />
                    <span>{r.label}</span>
                  </div>
                ))}
              </div>
            )}
            {errors.password && <span className="field__error">{errors.password.message}</span>}
          </div>

          {/* Confirm Password */}
          <div className="field">
            <label className="field__label">تأكيد كلمة المرور</label>
            <div className="field__input-wrapper">
              <input
                {...register('confirm_password')}
                type={showConfirm ? 'text' : 'password'}
                className={`field__input field__input--padded ${errors.confirm_password ? 'field__input--error' : ''}`}
                placeholder="••••••••"
                dir="ltr"
              />
              <button type="button" className="field__eye" onClick={() => setShowConfirm(v => !v)} tabIndex={-1}>
                {showConfirm ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
            {errors.confirm_password && <span className="field__error">{errors.confirm_password.message}</span>}
          </div>

          {/* Submit */}
          <button type="submit" className="auth-btn" disabled={isSubmitting}>
            {isSubmitting ? (
              <><Loader2 size={18} className="spin" /> جاري إنشاء الحساب...</>
            ) : (
              <><UserPlus size={18} /> إنشاء الحساب</>
            )}
          </button>

          <p className="auth-terms">
            بإنشاء حساب، أنت توافق على{' '}
            <a href="#" className="auth-terms__link">شروط الاستخدام</a>
            {' '}و{' '}
            <a href="#" className="auth-terms__link">سياسة الخصوصية</a>
          </p>
        </form>

        <div className="auth-footer">
          <span>لديك حساب بالفعل؟</span>
          <Link to="/auth/login" className="auth-footer__link">تسجيل الدخول</Link>
        </div>
      </motion.div>
    </div>
  )
}
