/**
 * PublicRegistrationPage.tsx
 * Public event registration page shown to guests at /register/:slug — no auth required.
 * Renders custom fields, processes registration, and outputs live cards or pending messages.
 */
import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import {
  CalendarDays,
  MapPin,
  Clock,
  Sparkles,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Clock3,
  Download,
  QrCode,
} from 'lucide-react'
import { registrationApi, RegistrationFormField } from '../../events/api/registrationApi'
import './public-registration.css'

interface EventData {
  id: string
  title: string
  title_ar?: string
  start_date: string
  end_date?: string
  venue_name?: string
  venue_name_ar?: string
  venue_address?: string
  cover_image_url?: string
}

interface FormSettings {
  is_enabled: boolean
  fields: RegistrationFormField[]
  success_message_ar?: string
  success_message_en?: string
  pending_approval_message_ar?: string
  pending_approval_message_en?: string
}

export default function PublicRegistrationPage() {
  const { slug } = useParams<{ slug: string }>()
  
  // ── States ──
  const [event, setEvent] = useState<EventData | null>(null)
  const [formSettings, setFormSettings] = useState<FormSettings | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // ── Form Inputs ──
  const [guestName, setGuestName] = useState('')
  const [guestPhone, setGuestPhone] = useState('')
  const [guestEmail, setGuestEmail] = useState('')
  const [customAnswers, setCustomAnswers] = useState<Record<string, any>>({})
  const [activeDropdownId, setActiveDropdownId] = useState<string | null>(null)
  
  // ── Click outside handler for multiselect dropdowns ──
  useEffect(() => {
    const handleGlobalClick = () => {
      setActiveDropdownId(null)
    }
    window.addEventListener('click', handleGlobalClick)
    return () => window.removeEventListener('click', handleGlobalClick)
  }, [])

  const handleMultiselectToggle = (fieldId: string, option: string) => {
    const current = customAnswers[fieldId] || []
    let updated: string[]
    if (current.includes(option)) {
      updated = current.filter((o: string) => o !== option)
    } else {
      updated = [...current, option]
    }
    setCustomAnswers(prev => ({ ...prev, [fieldId]: updated }))
  }

  const handleCheckboxGroupToggle = (fieldId: string, option: string) => {
    const current = customAnswers[fieldId] || []
    let updated: string[]
    if (current.includes(option)) {
      updated = current.filter((o: string) => o !== option)
    } else {
      updated = [...current, option]
    }
    setCustomAnswers(prev => ({ ...prev, [fieldId]: updated }))
  }

  const handleRadioGroupSelect = (fieldId: string, option: string) => {
    setCustomAnswers(prev => ({ ...prev, [fieldId]: option }))
  }
  
  // ── Form Submit States ──
  const [submitting, setSubmitting] = useState(false)
  const [submitResult, setSubmitResult] = useState<{
    status: string
    message: string
    mode: string
    invitation?: any
  } | null>(null)
  const [downloading, setDownloading] = useState(false)

  // ── Fetch Event Info on Load ──
  useEffect(() => {
    if (!slug) return
    setLoading(true)
    registrationApi.getPublicRegisterInfo(slug)
      .then((data) => {
        setEvent(data.event)
        setFormSettings(data.form)
      })
      .catch((err) => {
        if (err.response?.status === 404) {
          setError('الحدث غير موجود')
        } else {
          setError('حدث خطأ أثناء تحميل تفاصيل التسجيل')
        }
      })
      .finally(() => setLoading(false))
  }, [slug])

  // ── Form Validation ──
  const validateForm = () => {
    if (!guestName.trim()) {
      alert('الرجاء إدخال الاسم بالكامل')
      return false
    }
    if (!guestPhone.trim()) {
      alert('الرجاء إدخال رقم الجوال')
      return false
    }

    // Check custom required fields
    if (formSettings?.fields) {
      for (const field of formSettings.fields) {
        if (field.system) continue
        if (field.required) {
          const ans = customAnswers[field.id]
          if (Array.isArray(ans)) {
            if (ans.length === 0) {
              alert(`الرجاء تحديد خيار واحد على الأقل لحقل: ${field.label}`)
              return false
            }
          } else if (ans === undefined || ans === null || (typeof ans === 'string' && !ans.trim()) || ans === false) {
            alert(`الرجاء إدخال أو تحديد حقل: ${field.label}`)
            return false
          }
        }
      }
    }
    return true
  }

  // ── Form Submission ──
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!slug || !validateForm()) return

    setSubmitting(true)
    try {
      const payload = {
        guest_name: guestName.trim(),
        guest_phone: guestPhone.trim(),
        guest_email: guestEmail.trim() || undefined,
        custom_answers: customAnswers
      }
      
      const res = await registrationApi.submitPublicRegistration(slug, payload)
      setSubmitResult(res)
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'فشل التسجيل، يرجى المحاولة لاحقاً'
      alert(msg)
    } finally {
      setSubmitting(false)
    }
  }

  // ── Card Download ──
  const handleDownloadTicket = async () => {
    if (!submitResult?.invitation) return
    const invitation = submitResult.invitation
    const imageUrl = invitation.card_image_url || invitation.barcode_png_url
    if (!imageUrl) return

    setDownloading(true)
    try {
      const response = await fetch(imageUrl)
      const blob = await response.blob()
      const blobUrl = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = blobUrl
      link.download = `بطاقة_دخول_${invitation.guest_name || 'تذكرة'}.png`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(blobUrl)
    } catch {
      window.open(imageUrl, '_blank')
    } finally {
      setDownloading(false)
    }
  }

  const handleCustomFieldChange = (fieldId: string, val: any) => {
    setCustomAnswers(prev => ({
      ...prev,
      [fieldId]: val
    }))
  }

  // ── Loading state ──
  if (loading) {
    return (
      <div className="public-reg-container">
        <Loader2 size={40} className="spin" style={{ color: '#6366f1' }} />
        <p style={{ marginTop: 16 }}>جاري تحميل تفاصيل التسجيل للحدث...</p>
      </div>
    )
  }

  // ── Error state ──
  if (error || !event || !formSettings) {
    return (
      <div className="public-reg-container">
        <div className="public-reg-card" style={{ padding: 40, textAlign: 'center' }}>
          <AlertCircle size={48} style={{ color: '#ef4444', margin: '0 auto 16px' }} />
          <h2>{error || 'الحدث غير متوفر'}</h2>
        </div>
      </div>
    )
  }

  // ── Registration Disabled ──
  if (!formSettings.is_enabled && !submitResult) {
    return (
      <div className="public-reg-container">
        <div className="public-reg-card" style={{ padding: 40, textAlign: 'center' }}>
          <AlertCircle size={48} style={{ color: '#f59e0b', margin: '0 auto 16px' }} />
          <h2>التسجيل مغلق</h2>
          <p style={{ color: '#9ca3af', marginTop: 8 }}>التسجيل الذاتي مغلق حالياً لهذا الحدث. يرجى التواصل مع المنظمين للمزيد من المعلومات.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="public-reg-container" dir="rtl">
      <div className="public-reg-card">
        {/* Event Cover Image */}
        {event.cover_image_url ? (
          <img src={event.cover_image_url} alt="Event Cover" className="public-reg-cover" />
        ) : (
          <div className="public-reg-placeholder-cover">
            <Sparkles size={40} />
          </div>
        )}

        {/* ── SUCCESS STATE VIEW ── */}
        {submitResult ? (
          <div className="public-success-view">
            {submitResult.mode === 'immediate' ? (
              <>
                <div className="success-icon-wrapper">
                  <CheckCircle2 size={42} />
                </div>
                <h2>تم تسجيلك بنجاح!</h2>
                <p>{submitResult.message}</p>

                {/* Card/Barcode Preview Box */}
                <div className="ticket-preview-box">
                  {submitResult.invitation.card_image_url || submitResult.invitation.barcode_png_url ? (
                    <img
                      src={submitResult.invitation.card_image_url || submitResult.invitation.barcode_png_url}
                      alt="بطاقة الحضور"
                      className="ticket-preview-img"
                    />
                  ) : (
                    <div className="ticket-placeholder-img">
                      <QrCode size={48} />
                      <span>توليد التذكرة...</span>
                    </div>
                  )}
                </div>

                <div className="success-actions">
                  <button
                    className="public-submit-btn"
                    onClick={handleDownloadTicket}
                    disabled={downloading}
                  >
                    {downloading ? (
                      <Loader2 className="spin" size={16} />
                    ) : (
                      <Download size={16} />
                    )}
                    حفظ وتحميل بطاقة الدخول
                  </button>
                </div>
              </>
            ) : (
              <>
                <div className="success-icon-wrapper pending">
                  <Clock3 size={42} />
                </div>
                <h2>طلب التسجيل قيد المراجعة</h2>
                <p>{submitResult.message}</p>
                <div style={{ padding: '16px 20px', background: 'rgba(255, 255, 255, 0.03)', borderRadius: 12, marginTop: 12, fontSize: 13, color: '#9ca3af', width: '100%', maxWidth: 400 }}>
                  سوف يتم مراجعة طلبك من قبل الجهة المنظمة، وسيتم التواصل معك مباشرة وإرسال بطاقة الدخول عند قبول طلب التسجيل.
                </div>
              </>
            )}
          </div>
        ) : (
          /* ── FORM STATE VIEW ── */
          <>
            <div className="public-reg-header">
              <h1>{event.title_ar || event.title}</h1>
              
              <div className="event-brief-details">
                <div className="detail-item">
                  <CalendarDays size={14} />
                  <span>
                    {new Date(event.start_date).toLocaleDateString('ar-SA', {
                      weekday: 'long',
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric',
                    })}
                  </span>
                </div>
                <div className="detail-item">
                  <Clock size={14} />
                  <span>
                    {new Date(event.start_date).toLocaleTimeString('ar-SA', {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </span>
                </div>
                {event.venue_name_ar || event.venue_name ? (
                  <div className="detail-item">
                    <MapPin size={14} />
                    <span>{event.venue_name_ar || event.venue_name}</span>
                  </div>
                ) : null}
              </div>
            </div>

            <div className="public-reg-body">
              <form onSubmit={handleSubmit} className="public-reg-form">
                {formSettings.fields.map((field) => {
                  // Render System Name Field
                  if (field.id === 'guest_name') {
                    return (
                      <div key={field.id} className="public-form-group">
                        <label>الاسم الكامل *</label>
                        <input
                          type="text"
                          required
                          className="public-form-control"
                          placeholder="الرجاء كتابة اسمك الكامل ثلاثياً"
                          value={guestName}
                          onChange={(e) => setGuestName(e.target.value)}
                        />
                      </div>
                    )
                  }

                  // Render System Phone Field
                  if (field.id === 'guest_phone') {
                    return (
                      <div key={field.id} className="public-form-group">
                        <label>رقم الجوال *</label>
                        <input
                          type="tel"
                          required
                          className="public-form-control"
                          placeholder="مثال: +9665xxxxxxxx"
                          value={guestPhone}
                          onChange={(e) => setGuestPhone(e.target.value)}
                        />
                      </div>
                    )
                  }

                  // Render System Email Field (if present)
                  if (field.id === 'guest_email') {
                    return (
                      <div key={field.id} className="public-form-group">
                        <label>البريد الإلكتروني {field.required && '*'}</label>
                        <input
                          type="email"
                          required={field.required}
                          className="public-form-control"
                          placeholder="example@domain.com"
                          value={guestEmail}
                          onChange={(e) => setGuestEmail(e.target.value)}
                        />
                      </div>
                    )
                  }

                  // Render Custom Fields dynamically
                  const val = customAnswers[field.id]

                  if (field.type === 'select') {
                    return (
                      <div key={field.id} className="public-form-group">
                        <label>{field.label} {field.required && '*'}</label>
                        <select
                          required={field.required}
                          className="public-form-control"
                          value={typeof val === 'string' ? val : ''}
                          onChange={(e) => handleCustomFieldChange(field.id, e.target.value)}
                        >
                          <option value="">اختر...</option>
                          {field.options?.map((opt, oIdx) => (
                            <option key={oIdx} value={opt}>
                              {opt}
                            </option>
                          ))}
                        </select>
                      </div>
                    )
                  }

                  if (field.type === 'multiselect') {
                    const selectedOpts = Array.isArray(val) ? val : []
                    return (
                      <div key={field.id} className="public-form-group">
                        <label>{field.label} {field.required && '*'}</label>
                        <div className="custom-multiselect-container">
                          <div
                            className={`multiselect-trigger ${activeDropdownId === field.id ? 'open' : ''}`}
                            onClick={(e) => {
                              e.stopPropagation()
                              setActiveDropdownId(activeDropdownId === field.id ? null : field.id)
                            }}
                          >
                            {selectedOpts.length > 0 ? (
                              <div className="multiselect-tags-container">
                                {selectedOpts.map((opt: string) => (
                                  <span key={opt} className="multiselect-tag" onClick={(e) => e.stopPropagation()}>
                                    {opt}
                                    <button
                                      type="button"
                                      className="multiselect-tag-remove"
                                      onClick={(e) => {
                                        e.stopPropagation()
                                        handleMultiselectToggle(field.id, opt)
                                      }}
                                    >
                                      &times;
                                    </button>
                                  </span>
                                ))}
                              </div>
                            ) : (
                              <span className="multiselect-placeholder">اختر من القائمة...</span>
                            )}
                          </div>

                          {activeDropdownId === field.id && (
                            <div className="multiselect-dropdown" onClick={(e) => e.stopPropagation()}>
                              {field.options?.map((opt, oIdx) => {
                                const isChecked = selectedOpts.includes(opt)
                                return (
                                  <div
                                    key={oIdx}
                                    className="multiselect-option"
                                    onClick={() => handleMultiselectToggle(field.id, opt)}
                                  >
                                    <input
                                      type="checkbox"
                                      checked={isChecked}
                                      readOnly
                                    />
                                    <span>{opt}</span>
                                  </div>
                                )
                              })}
                            </div>
                          )}
                        </div>
                      </div>
                    )
                  }

                  if (field.type === 'checkbox_group') {
                    const selectedOpts = Array.isArray(val) ? val : []
                    return (
                      <div key={field.id} className="public-form-group">
                        <label>{field.label} {field.required && '*'}</label>
                        <div className="checkbox-group-container">
                          {field.options?.map((opt, oIdx) => {
                            const isChecked = selectedOpts.includes(opt)
                            return (
                              <label
                                key={oIdx}
                                className={`checkbox-group-option ${isChecked ? 'selected' : ''}`}
                              >
                                <input
                                  type="checkbox"
                                  checked={isChecked}
                                  onChange={() => handleCheckboxGroupToggle(field.id, opt)}
                                />
                                <span>{opt}</span>
                              </label>
                            )
                          })}
                        </div>
                      </div>
                    )
                  }

                  if (field.type === 'radio_group') {
                    const selectedVal = typeof val === 'string' ? val : ''
                    return (
                      <div key={field.id} className="public-form-group">
                        <label>{field.label} {field.required && '*'}</label>
                        <div className="radio-group-container">
                          {field.options?.map((opt, oIdx) => {
                            const isSelected = selectedVal === opt
                            return (
                              <label
                                key={oIdx}
                                className={`radio-group-option ${isSelected ? 'selected' : ''}`}
                              >
                                <input
                                  type="radio"
                                  name={`radio_g_${field.id}`}
                                  checked={isSelected}
                                  onChange={() => handleRadioGroupSelect(field.id, opt)}
                                />
                                <span>{opt}</span>
                              </label>
                            )
                          })}
                        </div>
                      </div>
                    )
                  }

                  if (field.type === 'checkbox') {
                    return (
                      <div key={field.id} className="public-form-group">
                        <label className="public-checkbox-container">
                          <input
                            type="checkbox"
                            required={field.required}
                            checked={Boolean(val)}
                            onChange={(e) => handleCustomFieldChange(field.id, e.target.checked)}
                          />
                          <span>{field.label} {field.required && '*'}</span>
                        </label>
                      </div>
                    )
                  }

                  // Standard types (text, number, email, date)
                  return (
                    <div key={field.id} className="public-form-group">
                      <label>{field.label} {field.required && '*'}</label>
                      <input
                        type={field.type}
                        required={field.required}
                        className="public-form-control"
                        value={typeof val === 'string' || typeof val === 'number' ? val : ''}
                        onChange={(e) => handleCustomFieldChange(field.id, e.target.value)}
                      />
                    </div>
                  )
                })}

                <button
                  type="submit"
                  className="public-submit-btn"
                  disabled={submitting}
                >
                  {submitting ? (
                    <>
                      <Loader2 className="spin" size={16} />
                      جاري التسجيل...
                    </>
                  ) : (
                    <>
                      <Sparkles size={16} />
                      تسجيل الحضور وتأكيد الطلب
                    </>
                  )}
                </button>
              </form>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
