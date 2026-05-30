import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { motion } from 'framer-motion'
import { Eye, EyeOff, LogIn, Loader2, AlertCircle } from 'lucide-react'
import { authAPI } from '../api/authApi'
import { useAuthStore } from '../store/authStore'
import type { AuthUser } from '../types'
import './auth.css'

const schema = z.object({
  email:    z.string().email('بريد إلكتروني غير صالح'),
  password: z.string().min(6, 'كلمة المرور يجب أن تكون 6 أحرف على الأقل'),
})
type FormData = z.infer<typeof schema>

export default function LoginPage() {
  const navigate  = useNavigate()
  const setAuth   = useAuthStore(s => s.setAuth)
  const [showPassword, setShowPassword] = useState(false)
  const [serverError, setServerError]   = useState('')

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) })

  const onSubmit = async (data: FormData) => {
    setServerError('')
    try {
      const res = await authAPI.login(data)

      const user: AuthUser = {
        id:         res.user_id!,
        email:      data.email,
        full_name:  null,
        avatar_url: null,
        is_staff:   false,
      }

      setAuth(user, res.tenants || [])
      navigate('/dashboard', { replace: true })
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } }
      setServerError(e?.response?.data?.detail || 'حدث خطأ، حاول مرة أخرى')
    }
  }

  return (
    <div className="auth-page">
      {/* Background Orbs */}
      <div className="auth-orb auth-orb--1" />
      <div className="auth-orb auth-orb--2" />

      <motion.div
        className="auth-card"
        initial={{ opacity: 0, y: 24, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.5, ease: [0.34, 1.56, 0.64, 1] }}
      >
        {/* Logo */}
        <div className="auth-logo">
          <img src="/logo.png" alt="Qentry" className="auth-logo__img" />
        </div>

        <div className="auth-header">
          <h1 className="auth-title">مرحباً بعودتك</h1>
          <p className="auth-subtitle">سجّل دخولك للمتابعة</p>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="auth-form" noValidate>

          {/* Server Error */}
          {serverError && (
            <motion.div
              className="auth-error"
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <AlertCircle size={16} />
              <span>{serverError}</span>
            </motion.div>
          )}

          {/* Email */}
          <div className="field">
            <label className="field__label">البريد الإلكتروني</label>
            <input
              {...register('email')}
              type="email"
              className={`field__input ${errors.email ? 'field__input--error' : ''}`}
              placeholder="you@example.com"
              autoComplete="email"
              dir="ltr"
            />
            {errors.email && (
              <span className="field__error">{errors.email.message}</span>
            )}
          </div>

          {/* Password */}
          <div className="field">
            <div className="field__label-row">
              <label className="field__label">كلمة المرور</label>
              <Link to="/auth/forgot-password" className="field__link">
                نسيت كلمة المرور؟
              </Link>
            </div>
            <div className="field__input-wrapper">
              <input
                {...register('password')}
                type={showPassword ? 'text' : 'password'}
                className={`field__input field__input--padded ${errors.password ? 'field__input--error' : ''}`}
                placeholder="••••••••"
                autoComplete="current-password"
                dir="ltr"
              />
              <button
                type="button"
                className="field__eye"
                onClick={() => setShowPassword(v => !v)}
                tabIndex={-1}
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
            {errors.password && (
              <span className="field__error">{errors.password.message}</span>
            )}
          </div>

          {/* Submit */}
          <button type="submit" className="auth-btn" disabled={isSubmitting}>
            {isSubmitting ? (
              <><Loader2 size={18} className="spin" /> جاري تسجيل الدخول...</>
            ) : (
              <><LogIn size={18} /> تسجيل الدخول</>
            )}
          </button>

        </form>

        <div className="auth-footer">
          <span>ليس لديك حساب؟</span>
          <Link to="/auth/signup" className="auth-footer__link">إنشاء حساب جديد</Link>
        </div>
      </motion.div>
    </div>
  )
}
