/**
 * EventRegistrationTab.tsx
 * Overhauled Premium Admin UI for configuring event self-registration forms, dynamic fields,
 * public registration link delivery, and ticket generation behavior.
 */
import { useState, useEffect } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import {
  Settings,
  ClipboardList,
  Sparkles,
  Plus,
  Trash2,
  ArrowUp,
  ArrowDown,
  FileCheck,
  CheckCircle,
  Loader2,
  Copy,
  ExternalLink,
  QrCode,
  Lock,
  Download,
  AlertCircle,
  X,
  Users
} from 'lucide-react'
import { useAuthStore } from '@features/auth/store/authStore'
import { registrationApi, RegistrationFormCreate, RegistrationFormField } from '../api/registrationApi'
import { templatesApi } from '../api/templatesApi'
import { useInvitationsList, useUpdateInvitation } from '@features/invitations/hooks/useInvitations'
import './event-registration.css'

interface Props {
  event: {
    id: string
    slug: string | null
    title: string
  }
  isActiveTab: boolean
}

export function EventRegistrationTab({ event, isActiveTab }: Props) {
  const tenantId = useAuthStore((s) => s.currentTenantId)
  const eventId = event.id

  // ── Local Settings State ──
  const [isEnabled, setIsEnabled] = useState(false)
  const [generationMode, setGenerationMode] = useState<'immediate' | 'deferred'>('immediate')
  const [ticketClass, setTicketClass] = useState<'vip' | 'normal'>('normal')
  const [templateId, setTemplateId] = useState<string>('')
  const [successMessageAr, setSuccessMessageAr] = useState('')
  const [successMessageEn, setSuccessMessageEn] = useState('')
  const [pendingMessageAr, setPendingMessageAr] = useState('')
  const [pendingMessageEn, setPendingMessageEn] = useState('')

  // ── Dynamic Fields State ──
  const [fields, setFields] = useState<RegistrationFormField[]>([
    { id: 'guest_name', type: 'text', label: 'الاسم الكامل', label_en: 'Full Name', required: true, system: true },
    { id: 'guest_phone', type: 'phone', label: 'رقم الجوال', label_en: 'Phone Number', required: true, system: true },
  ])

  // ── Temporary State for adding a new field ──
  const [newFieldLabel, setNewFieldLabel] = useState('')
  const [newFieldLabelEn, setNewFieldLabelEn] = useState('')
  const [newFieldType, setNewFieldType] = useState<RegistrationFormField['type']>('text')
  const [newFieldRequired, setNewFieldRequired] = useState(false)
  const [newFieldOptions, setNewFieldOptions] = useState('')

  // ── Copy Link Feedback State ──
  const [copied, setCopied] = useState(false)

  // Calculate public registration URL
  const registerUrl = `${window.location.origin}/register/${event.slug || ''}`

  // ── Applicants Management States ──
  const [showApplicantsModal, setShowApplicantsModal] = useState(false)
  const [applicantStatusFilter, setApplicantStatusFilter] = useState<'all' | 'pending' | 'accepted' | 'declined'>('all')
  const [applicantSearch, setApplicantSearch] = useState('')
  const [expandedApplicantId, setExpandedApplicantId] = useState<string | null>(null)

  // ── Query List of Applicants for this specific event ──
  const { data: invitations, isLoading: isLoadingInvs, refetch: refetchInvs } = useInvitationsList({
    event_id: eventId,
    limit: 500
  })

  // ── Stats Calculations ──
  const registeredGuests = invitations?.filter(inv => {
    const isFromForm = inv.metadata && (
      inv.metadata.is_registration === true || 
      (inv.metadata.custom_fields && Object.keys(inv.metadata.custom_fields).length > 0)
    );
    return isFromForm && ['pending', 'accepted', 'declined'].includes(inv.rsvp_status || '');
  }) || []
  const totalApplicants = registeredGuests.length
  const pendingCount = registeredGuests.filter(inv => inv.rsvp_status === 'pending').length
  const acceptedCount = registeredGuests.filter(inv => inv.rsvp_status === 'accepted').length
  const declinedCount = registeredGuests.filter(inv => inv.rsvp_status === 'declined').length

  const updateMutation = useUpdateInvitation()

  const handleApproveApplicant = (invId: string) => {
    updateMutation.mutate({
      id: invId,
      data: { status: 'accepted', rsvp_status: 'accepted' }
    }, {
      onSuccess: () => {
        refetchInvs()
        alert('تم قبول طلب التسجيل وتوليد الباركود وبطاقة الدخول بنجاح')
      },
      onError: (err: any) => {
        alert(`فشل قبول الطلب: ${err.message || err}`)
      }
    })
  }

  const handleDeclineApplicant = (invId: string) => {
    if (confirm('هل أنت متأكد من رفض هذا الطلب؟')) {
      updateMutation.mutate({
        id: invId,
        data: { status: 'declined', rsvp_status: 'declined' }
      }, {
        onSuccess: () => {
          refetchInvs()
          alert('تم رفض طلب التسجيل بنجاح')
        },
        onError: (err: any) => {
          alert(`فشل رفض الطلب: ${err.message || err}`)
        }
      })
    }
  }

  const handleExportApplicants = () => {
    if (!invitations) return
    const list = invitations.filter(inv => {
      const isFromForm = inv.metadata && (
        inv.metadata.is_registration === true || 
        (inv.metadata.custom_fields && Object.keys(inv.metadata.custom_fields).length > 0)
      );
      return isFromForm && ['pending', 'accepted', 'declined'].includes(inv.rsvp_status || '');
    })
    if (list.length === 0) {
      alert('لا يوجد مسجلين لتصديرهم')
      return
    }
    
    const headers = ["الاسم", "رقم الجوال", "البريد الإلكتروني", "الحالة", "تاريخ التسجيل", "الخيارات المخصصة"]
    const rows = list.map(inv => {
      const answers = inv.metadata?.custom_fields
        ? Object.entries(inv.metadata.custom_fields)
            .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
            .join(' | ')
        : ''
      const statusTxt = inv.rsvp_status === 'accepted' ? 'مقبول' : (inv.rsvp_status === 'declined' ? 'مرفوض' : 'قيد الانتظار')
      return [
        inv.guest_name || inv.guest_name_ar || '',
        inv.guest_phone || '',
        inv.guest_email || '',
        statusTxt,
        inv.created_at ? new Date(inv.created_at).toLocaleString('ar-SA') : '',
        answers
      ]
    })
    
    const csvContent = "\uFEFF" + [
      headers.map(h => `"${h}"`).join(','),
      ...rows.map(r => r.map(val => `"${String(val).replace(/"/g, '""')}"`).join(','))
    ].join('\r\n')
    
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a")
    link.setAttribute("href", url)
    link.setAttribute("download", `مسجلي_الحدث_${event.title}.csv`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  // ── Load registration form settings ──
  const { data: formSettings, isLoading: isLoadingForm, refetch: refetchForm } = useQuery({
    queryKey: ['registrationForm', eventId, tenantId],
    queryFn: () => registrationApi.getRegistrationForm(eventId),
    enabled: isActiveTab && !!tenantId,
  })

  // ── Load event templates ──
  const { data: templates } = useQuery({
    queryKey: ['templates', eventId, tenantId],
    queryFn: () => templatesApi.list(eventId),
    enabled: isActiveTab && !!tenantId,
  })

  // ── Synchronize state from API ──
  useEffect(() => {
    if (formSettings) {
      setIsEnabled(formSettings.is_enabled)
      setGenerationMode(formSettings.barcode_generation_mode as 'immediate' | 'deferred')
      setTicketClass(formSettings.default_ticket_class as 'vip' | 'normal')
      setTemplateId(formSettings.default_template_id || '')
      setSuccessMessageAr(formSettings.success_message_ar || '')
      setSuccessMessageEn(formSettings.success_message_en || '')
      setPendingMessageAr(formSettings.pending_approval_message_ar || '')
      setPendingMessageEn(formSettings.pending_approval_message_en || '')
      
      const loadedFields = formSettings.fields || []
      const systemFields = [
        { id: 'guest_name', type: 'text', label: 'الاسم الكامل', label_en: 'Full Name', required: true, system: true },
        { id: 'guest_phone', type: 'phone', label: 'رقم الجوال', label_en: 'Phone Number', required: true, system: true },
      ] as RegistrationFormField[]

      const customFields = loadedFields.filter(f => !f.system)
      setFields([...systemFields, ...customFields])
    }
  }, [formSettings])

  // ── Copy Link Action ──
  const handleCopyLink = () => {
    navigator.clipboard.writeText(registerUrl)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  // ── QR Download Action ──
  const downloadQrCode = async () => {
    const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=500x500&data=${encodeURIComponent(registerUrl)}`
    try {
      const response = await fetch(qrUrl)
      const blob = await response.blob()
      const blobUrl = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = blobUrl
      link.download = `QR_تسجيل_${event.title || 'حدث'}.png`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(blobUrl)
    } catch {
      window.open(qrUrl, '_blank')
    }
  }

  // ── Save Mutation ──
  const saveMutation = useMutation({
    mutationFn: (data: RegistrationFormCreate) => registrationApi.saveRegistrationForm(eventId, data),
    onSuccess: () => {
      refetchForm()
      alert('تم حفظ إعدادات التسجيل بنجاح')
    },
    onError: (err: any) => {
      alert(`فشل الحفظ: ${err.message || err}`)
    }
  })

  const handleSave = () => {
    const payload: RegistrationFormCreate = {
      is_enabled: isEnabled,
      barcode_generation_mode: generationMode,
      default_ticket_class: ticketClass,
      default_template_id: templateId || null,
      success_message_ar: successMessageAr || null,
      success_message_en: successMessageEn || null,
      pending_approval_message_ar: pendingMessageAr || null,
      pending_approval_message_en: pendingMessageEn || null,
      fields: fields,
    }
    saveMutation.mutate(payload)
  }

  // ── Custom Field Handlers ──
  const addCustomField = () => {
    if (!newFieldLabel.trim()) return
    const cleanLabel = newFieldLabel.trim()
    const cleanLabelEn = newFieldLabelEn.trim()
    const fieldId = `cf_${Date.now()}`

    const newField: RegistrationFormField = {
      id: fieldId,
      type: newFieldType,
      label: cleanLabel,
      label_en: cleanLabelEn || undefined,
      required: newFieldRequired,
      system: false,
      options: ['select', 'multiselect', 'checkbox_group', 'radio_group'].includes(newFieldType) && newFieldOptions.trim()
        ? newFieldOptions.split(',').map(s => s.trim()).filter(Boolean)
        : undefined
    }

    setFields([...fields, newField])
    setNewFieldLabel('')
    setNewFieldLabelEn('')
    setNewFieldRequired(false)
    setNewFieldOptions('')
  }

  const removeField = (id: string) => {
    setFields(fields.filter(f => f.id !== id))
  }

  const toggleFieldRequired = (id: string) => {
    setFields(fields.map(f => f.id === id ? { ...f, required: !f.required } : f))
  }

  const moveField = (index: number, direction: 'up' | 'down') => {
    if (direction === 'up' && index === 2) return // Locked system fields
    if (direction === 'down' && index === fields.length - 1) return

    const newFields = [...fields]
    const swapTarget = direction === 'up' ? index - 1 : index + 1
    const temp = newFields[index]
    newFields[index] = newFields[swapTarget]
    newFields[swapTarget] = temp
    setFields(newFields)
  }

  if (!isActiveTab) return null

  if (isLoadingForm) {
    return (
      <div className="event-reg-loading">
        <Loader2 className="spin" size={32} />
        <p>جاري تحميل إعدادات نموذج التسجيل...</p>
      </div>
    )
  }

  return (
    <div className="event-registration-tab-overhaul" dir="rtl">
      
      {/* ── SECTION HEADER & PUBLIC URL SHARING PANEL ── */}
      <div className="premium-sharing-header glass-panel">
        <div className="header-text-block">
          <div className="badge-row">
            <span className={`status-badge-glow ${isEnabled ? 'enabled' : 'disabled'}`}>
              ● {isEnabled ? 'النموذج نشط ومتاح للعامة' : 'التسجيل مغلق'}
            </span>
          </div>
          <h2>رابط تسجيل الحضور العام</h2>
          <p>شارك الرابط أو رمز الـ QR أدناه مع ضيوفك ليتمكنوا من حجز مقاعدهم وتسجيل حضورهم ذاتياً.</p>
          
          <div className="premium-link-bar">
            <input type="text" readOnly value={registerUrl} className="share-url-input" />
            <button className={`share-action-btn copy-btn ${copied ? 'copied' : ''}`} onClick={handleCopyLink}>
              <Copy size={15} />
              <span>{copied ? 'تم النسخ!' : 'نسخ الرابط'}</span>
            </button>
            <a href={registerUrl} target="_blank" rel="noreferrer" className="share-action-btn preview-btn">
              <ExternalLink size={15} />
              <span>معاينة الصفحة</span>
            </a>
            <button
              onClick={() => {
                refetchInvs()
                setShowApplicantsModal(true)
              }}
              className="share-action-btn copy-btn"
              style={{ background: 'linear-gradient(135deg, #C9A96E 0%, #b08b47 100%)', color: '#0f172a', fontWeight: 'bold' }}
            >
              <ClipboardList size={15} />
              <span>استعراض المسجلين ({totalApplicants})</span>
            </button>
          </div>
        </div>
        
        {/* Interactive QR Block */}
        <div className="premium-qr-block" onClick={downloadQrCode} title="اضغط لتحميل كود QR">
          <div className="qr-image-wrapper">
            <img
              src={`https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=${encodeURIComponent(registerUrl)}`}
              alt="QR Code"
            />
            <div className="qr-hover-overlay">
              <Download size={18} />
              <span>تحميل QR</span>
            </div>
          </div>
          <span className="qr-subtext"><QrCode size={12} /> اضغط لحفظ الرمز</span>
        </div>
      </div>

      {/* ── APPLICANTS QUICK STATS & MANAGEMENT ROW ── */}
      <div className="applicants-stats-panel glass-panel">
        <div className="stats-grid-row">
          <div className="stat-item-card">
            <span className="stat-value">{totalApplicants}</span>
            <span className="stat-label">إجمالي المسجلين</span>
          </div>
          <div className="stat-item-card pending-highlight">
            <span className="stat-value">{pendingCount}</span>
            <span className="stat-label">بانتظار الموافقة</span>
          </div>
          <div className="stat-item-card accepted-highlight">
            <span className="stat-value">{acceptedCount}</span>
            <span className="stat-label">تم قبولهم</span>
          </div>
          <div className="stat-item-card">
            <span className="stat-value">{declinedCount}</span>
            <span className="stat-label">المرفوضين</span>
          </div>
        </div>
        <div className="manage-action-container">
          <button
            onClick={() => {
              refetchInvs()
              setShowApplicantsModal(true)
            }}
            className="btn-manage-applicants"
          >
            <Users size={16} />
            <span>عرض وإدارة طلبات التسجيل</span>
          </button>
        </div>
      </div>

      {/* ── TWO-COLUMN CONFIGURATION LAYOUT ── */}
      <div className="registration-grid-overhaul">
        
        {/* RIGHT COLUMN: Settings Card & Success Messages */}
        <div className="config-settings-column">
          
          {/* Main Activation Card */}
          <div className="premium-settings-card glass-panel">
            <div className="card-header-toggle">
              <div className="header-title">
                <Settings size={18} />
                <h3>حالة وإعدادات التفعيل</h3>
              </div>
              <div className="modern-switch-wrapper">
                <button
                  className={`modern-switch-toggle ${isEnabled ? 'on' : 'off'}`}
                  onClick={() => setIsEnabled(!isEnabled)}
                >
                  <span className="modern-switch-slider"></span>
                </button>
              </div>
            </div>
            
            <div className="settings-field-group">
              <label>آلية توليد وإصدار التذاكر</label>
              <div className="mode-selection-cards">
                
                <div
                  className={`mode-card-premium ${generationMode === 'immediate' ? 'active-immediate' : ''}`}
                  onClick={() => setGenerationMode('immediate')}
                >
                  <div className="mode-card-header">
                    <CheckCircle className="mode-icon" size={18} />
                    <h4>إصدار فوري ومباشر</h4>
                  </div>
                  <p>توليد باركود تذكرة الدخول وإرسالها فورياً للضيف بمجرد إرسال النموذج بنجاح.</p>
                </div>

                <div
                  className={`mode-card-premium ${generationMode === 'deferred' ? 'active-deferred' : ''}`}
                  onClick={() => setGenerationMode('deferred')}
                >
                  <div className="mode-card-header">
                    <FileCheck className="mode-icon" size={18} />
                    <h4>مراجعة وقبول المنظم</h4>
                  </div>
                  <p>حفظ الطلب كـ "قيد الانتظار". لا يتم توليد باركود التذكرة إلا بعد قبول الطلب يدوياً.</p>
                </div>

              </div>
            </div>

            <div className="dropdowns-split-row">
              <div className="settings-field-group">
                <label>الفئة الافتراضية للبطاقة</label>
                <select
                  className="premium-select-input"
                  value={ticketClass}
                  onChange={(e) => setTicketClass(e.target.value as 'vip' | 'normal')}
                >
                  <option value="normal">🎫 عادي (Normal)</option>
                  <option value="vip">👑 VIP</option>
                </select>
              </div>

              <div className="settings-field-group">
                <label>قالب كرت الدعوة</label>
                <select
                  className="premium-select-input"
                  value={templateId}
                  onChange={(e) => setTemplateId(e.target.value)}
                >
                  <option value="">باركود فقط (تذكرة افتراضية)</option>
                  {templates?.map((t: any) => (
                    <option key={t.id} value={t.id}>
                      {t.name} ({t.template_type === 'designed' ? 'كرت مصمم' : 'سريع'})
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Feedback Messages Card */}
          <div className="premium-settings-card glass-panel">
            <div className="header-title">
              <ClipboardList size={18} />
              <h3>رسائل تأكيد التسجيل للضيوف</h3>
            </div>
            
            {generationMode === 'immediate' ? (
              <div className="messages-textareas-grid">
                <div className="settings-field-group">
                  <label>رسالة النجاح باللغة العربية (الفوري)</label>
                  <textarea
                    rows={3}
                    className="premium-textarea"
                    placeholder="مثال: تم تسجيلكم بنجاح! يمكنك تحميل بطاقة الدخول الخاصة بك الآن."
                    value={successMessageAr}
                    onChange={(e) => setSuccessMessageAr(e.target.value)}
                  />
                </div>
                <div className="settings-field-group">
                  <label>رسالة النجاح باللغة الإنجليزية (الفوري)</label>
                  <textarea
                    rows={3}
                    className="premium-textarea ltr-input"
                    placeholder="e.g. Registration successful! You can download your invitation card now."
                    value={successMessageEn}
                    onChange={(e) => setSuccessMessageEn(e.target.value)}
                  />
                </div>
              </div>
            ) : (
              <div className="messages-textareas-grid">
                <div className="settings-field-group">
                  <label>رسالة قيد المراجعة باللغة العربية (المؤجل)</label>
                  <textarea
                    rows={3}
                    className="premium-textarea"
                    placeholder="مثال: تم استلام طلبكم بنجاح وهو قيد المراجعة حالياً، وسيتم إرسال بطاقة الدخول فور الموافقة."
                    value={pendingMessageAr}
                    onChange={(e) => setPendingMessageAr(e.target.value)}
                  />
                </div>
                <div className="settings-field-group">
                  <label>رسالة قيد المراجعة باللغة الإنجليزية (المؤجل)</label>
                  <textarea
                    rows={3}
                    className="premium-textarea ltr-input"
                    placeholder="e.g. Request received! It is under review and you will receive your invitation card upon approval."
                    value={pendingMessageEn}
                    onChange={(e) => setPendingMessageEn(e.target.value)}
                  />
                </div>
              </div>
            )}
          </div>

        </div>

        {/* LEFT COLUMN: Fields List & Builder */}
        <div className="fields-management-column">
          
          <div className="premium-settings-card glass-panel">
            <div className="header-title">
              <ClipboardList size={18} />
              <h3>حقول نموذج التسجيل</h3>
            </div>

            {/* List of active fields */}
            <div className="premium-fields-list">
              {fields.map((field, index) => (
                <div key={field.id} className={`premium-field-row ${field.system ? 'system-locked' : 'custom-dynamic'}`}>
                  <div className="field-meta-info">
                    {field.system ? (
                      <span className="field-badge-lock"><Lock size={10} /> أساسي ومغلق</span>
                    ) : (
                      <span className="field-badge-custom">حقل مخصص</span>
                    )}
                    <span className="field-label-text">{field.label}</span>
                    {field.label_en && <span className="field-label-en">({field.label_en})</span>}
                    <span className="field-type-indicator">{field.type}</span>
                  </div>

                  <div className="field-row-controls">
                    <label className="checkbox-toggle-premium" title="تحديد كحقل مطلوب">
                      <input
                        type="checkbox"
                        checked={field.required}
                        disabled={field.system}
                        onChange={() => toggleFieldRequired(field.id)}
                      />
                      <span>مطلوب</span>
                    </label>

                    {!field.system && (
                      <div className="field-order-actions">
                        <button
                          className="btn-order"
                          disabled={index <= 2}
                          onClick={() => moveField(index, 'up')}
                          title="نقل للأعلى"
                        >
                          <ArrowUp size={12} />
                        </button>
                        <button
                          className="btn-order"
                          disabled={index === fields.length - 1}
                          onClick={() => moveField(index, 'down')}
                          title="نقل للأسفل"
                        >
                          <ArrowDown size={12} />
                        </button>
                        <button
                          className="btn-delete-field"
                          onClick={() => removeField(field.id)}
                          title="حذف الحقل"
                        >
                          <Trash2 size={13} />
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* Creator Box */}
            <div className="premium-creator-box">
              <div className="creator-title">
                <Plus size={14} />
                <h4>إضافة حقل مخصص جديد</h4>
              </div>
              
              <div className="creator-inputs-row">
                <div className="settings-field-group">
                  <label>اسم الحقل بالعربية *</label>
                  <input
                    type="text"
                    className="premium-select-input"
                    placeholder="مثال: جهة العمل"
                    value={newFieldLabel}
                    onChange={(e) => setNewFieldLabel(e.target.value)}
                  />
                </div>
                <div className="settings-field-group">
                  <label>اسم الحقل بالإنجليزية (اختياري)</label>
                  <input
                    type="text"
                    className="premium-select-input ltr-input"
                    placeholder="e.g. Workplace"
                    value={newFieldLabelEn}
                    onChange={(e) => setNewFieldLabelEn(e.target.value)}
                  />
                </div>
              </div>

              <div className="creator-inputs-row">
                <div className="settings-field-group">
                  <label>نوع البيانات</label>
                  <select
                    className="premium-select-input"
                    value={newFieldType}
                    onChange={(e) => setNewFieldType(e.target.value as RegistrationFormField['type'])}
                  >
                    <option value="text">🔤 نص قصير (Text)</option>
                    <option value="number">🔢 حقل رقمي (Number)</option>
                    <option value="email">📧 بريد إلكتروني (Email)</option>
                    <option value="phone">📞 رقم هاتف (Phone)</option>
                    <option value="select">🔽 قائمة خيارات منسدلة (Dropdown Select)</option>
                    <option value="multiselect">🗂️ خيارات متعددة (Multi-select Dropdown)</option>
                    <option value="checkbox_group">☑️ مجموعة مربعات تحديد (Checkbox Group)</option>
                    <option value="radio_group">🔘 أزرار خيار مفرد (Radio Buttons)</option>
                    <option value="date">📅 حقل تاريخ (Date)</option>
                    <option value="checkbox">☑️ مربع تحديد موافقة منفرد (Single Checkbox)</option>
                  </select>
                </div>
                <div className="settings-field-group center-vertical">
                  <label className="checkbox-toggle-premium outline-box">
                    <input
                      type="checkbox"
                      checked={newFieldRequired}
                      onChange={(e) => setNewFieldRequired(e.target.checked)}
                    />
                    <span>جعل هذا الحقل مطلوباً (Required)</span>
                  </label>
                </div>
              </div>

              {['select', 'multiselect', 'checkbox_group', 'radio_group'].includes(newFieldType) && (
                <div className="settings-field-group animated-fade">
                  <label>الخيارات المتاحة (مفصولة بفاصلة) *</label>
                  <input
                    type="text"
                    className="premium-select-input"
                    placeholder="مثال: قطاع حكومي, قطاع خاص, ريادي أعمال"
                    value={newFieldOptions}
                    onChange={(e) => setNewFieldOptions(e.target.value)}
                  />
                </div>
              )}

              <button className="btn-add-field-action" onClick={addCustomField}>
                <Plus size={14} />
                أضف الحقل لقائمة التسجيل
              </button>
            </div>

          </div>

        </div>

      </div>

      {/* ── FLOATING SAVE BAR ── */}
      <div className="premium-floating-save-bar glass-panel">
        <div className="info-badge">
          <AlertCircle size={14} />
          <span>تأكد من حفظ التعديلات لتطبيقها على صفحة التسجيل العامة للضيوف.</span>
        </div>
        <button
          className="btn-save-premium-glow"
          onClick={handleSave}
          disabled={saveMutation.isPending}
        >
          {saveMutation.isPending ? (
            <>
              <Loader2 className="spin" size={16} />
              جاري حفظ الإعدادات...
            </>
          ) : (
            <>
              <Sparkles size={16} />
              حفظ التعديلات والتفعيل
            </>
          )}
        </button>
      </div>

      {/* ── Applicants Management Modal ── */}
      {showApplicantsModal && (
        <div className="applicants-modal-overlay" onClick={() => setShowApplicantsModal(false)}>
          <div className="applicants-modal-panel" onClick={(e) => e.stopPropagation()}>
            <div className="applicants-modal-header">
              <div className="applicants-modal-title">
                <ClipboardList size={20} style={{ color: '#C9A96E' }} />
                <span>إدارة طلبات التسجيل والمتقدمين للحدث ({totalApplicants})</span>
              </div>
              <button className="applicants-modal-close" onClick={() => setShowApplicantsModal(false)}>
                <X size={18} />
              </button>
            </div>

            <div className="applicants-modal-body">
              {/* Toolbar in Modal: Search + Filter + Export */}
              <div className="applicants-modal-toolbar">
                <div style={{ display: 'flex', gap: 12, flex: 1, minWidth: '280px' }}>
                  <input
                    type="text"
                    placeholder="بحث باسم المسجل أو الهاتف..."
                    value={applicantSearch}
                    onChange={(e) => setApplicantSearch(e.target.value)}
                    className="applicants-search-input"
                  />
                  <select
                    value={applicantStatusFilter}
                    onChange={(e) => setApplicantStatusFilter(e.target.value as any)}
                    className="applicants-status-select"
                  >
                    <option value="all">جميع الحالات</option>
                    <option value="pending">قيد الانتظار والمراجعة</option>
                    <option value="accepted">المقبولين (تم إصدار كود)</option>
                    <option value="declined">المرفوضين</option>
                  </select>
                </div>
                
                <button className="btn-export-excel" onClick={handleExportApplicants}>
                  <Download size={14} />
                  <span>تصدير Excel</span>
                </button>
              </div>

              {/* Applicants Table */}
              {isLoadingInvs ? (
                <div style={{ textAlign: 'center', padding: '40px 0', color: '#9ca3af' }}>
                  <Loader2 className="spin" size={24} style={{ color: '#C9A96E', margin: '0 auto 12px' }} />
                  <span>جاري تحميل قائمة المسجلين...</span>
                </div>
              ) : !invitations || totalApplicants === 0 ? (
                <div style={{ textAlign: 'center', padding: '40px 20px', color: '#64748b' }}>
                  <Users size={32} style={{ margin: '0 auto 12px', opacity: 0.5 }} />
                  <h4>لا يوجد أي مسجلين لهذا الحدث بعد</h4>
                  <p style={{ fontSize: '0.8rem', marginTop: 4 }}>بمجرد قيام الضيوف بالتسجيل عبر الرابط العام، ستظهر طلباتهم هنا.</p>
                </div>
              ) : (
                <div className="table-container-glass">
                  <table className="applicants-table">
                    <thead>
                      <tr>
                        <th>الاسم الكامل</th>
                        <th>رقم الجوال</th>
                        <th>البريد الإلكتروني</th>
                        <th>تاريخ التقديم</th>
                        <th>الحالة</th>
                        <th>إجراءات</th>
                      </tr>
                    </thead>
                    <tbody>
                      {invitations
                        .filter(inv => {
                          const isFromForm = inv.metadata && (
                            inv.metadata.is_registration === true || 
                            (inv.metadata.custom_fields && Object.keys(inv.metadata.custom_fields).length > 0)
                          );
                          if (!isFromForm) return false;

                          const status = inv.rsvp_status || '';
                          const isApplicant = ['pending', 'accepted', 'declined'].includes(status);
                          if (!isApplicant) return false;
                          
                          const nameMatch = !applicantSearch || 
                            inv.guest_name?.toLowerCase().includes(applicantSearch.toLowerCase()) ||
                            inv.guest_name_ar?.includes(applicantSearch) ||
                            inv.guest_phone?.includes(applicantSearch);
                            
                          const statusMatch = applicantStatusFilter === 'all' || status === applicantStatusFilter;
                          return nameMatch && statusMatch;
                        })
                        .map((inv) => {
                          const isExpanded = expandedApplicantId === inv.id;
                          const answers = inv.metadata?.custom_fields || {};
                          const hasAnswers = Object.keys(answers).length > 0;
                          
                          return (
                            <>
                              <tr key={inv.id}>
                                <td style={{ fontWeight: 600, color: '#ffffff' }}>
                                  <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                                    <span>{inv.guest_name_ar || inv.guest_name}</span>
                                    {hasAnswers && (
                                      <button
                                        onClick={() => setExpandedApplicantId(isExpanded ? null : inv.id)}
                                        className="toggle-answers-btn"
                                      >
                                        <span>{isExpanded ? 'إخفاء الإجابات مخصصة ▲' : 'عرض إجابات الحقول المخصصة ▼'}</span>
                                      </button>
                                    )}
                                  </div>
                                </td>
                                <td style={{ color: '#d1d5db' }} dir="ltr">{inv.guest_phone}</td>
                                <td style={{ color: '#d1d5db' }}>{inv.guest_email || <span style={{ color: '#4b5563' }}>—</span>}</td>
                                <td style={{ color: '#9ca3af' }}>{new Date(inv.created_at).toLocaleDateString('ar-SA')}</td>
                                <td>
                                  <span style={{
                                    padding: '4px 10px',
                                    borderRadius: '20px',
                                    fontSize: '0.75rem',
                                    fontWeight: 700,
                                    background: inv.rsvp_status === 'accepted' ? 'rgba(16, 185, 129, 0.1)' : (inv.rsvp_status === 'declined' ? 'rgba(239, 68, 68, 0.1)' : 'rgba(245, 158, 11, 0.1)'),
                                    color: inv.rsvp_status === 'accepted' ? '#10b981' : (inv.rsvp_status === 'declined' ? '#ef4444' : '#f59e0b'),
                                    border: `1px solid ${inv.rsvp_status === 'accepted' ? 'rgba(16, 185, 129, 0.2)' : (inv.rsvp_status === 'declined' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(245, 158, 11, 0.2)')}`
                                  }}>
                                    {inv.rsvp_status === 'accepted' ? 'مقبول' : (inv.rsvp_status === 'declined' ? 'مرفوض' : 'قيد الانتظار')}
                                  </span>
                                </td>
                                <td>
                                  <div style={{ display: 'flex', gap: 6 }}>
                                    {inv.rsvp_status === 'pending' && (
                                      <>
                                        <button
                                          onClick={() => handleApproveApplicant(inv.id)}
                                          disabled={updateMutation.isPending}
                                          style={{
                                            padding: '6px 12px',
                                            background: '#C9A96E',
                                            color: '#0f172a',
                                            border: 'none',
                                            borderRadius: '6px',
                                            fontSize: '0.78rem',
                                            fontWeight: 700,
                                            cursor: 'pointer'
                                          }}
                                        >
                                          قبول
                                        </button>
                                        <button
                                          onClick={() => handleDeclineApplicant(inv.id)}
                                          disabled={updateMutation.isPending}
                                          style={{
                                            padding: '6px 12px',
                                            background: 'rgba(239, 68, 68, 0.1)',
                                            color: '#ef4444',
                                            border: '1px solid rgba(239, 68, 68, 0.2)',
                                            borderRadius: '6px',
                                            fontSize: '0.78rem',
                                            fontWeight: 700,
                                            cursor: 'pointer'
                                          }}
                                        >
                                          رفض
                                        </button>
                                      </>
                                    )}
                                  </div>
                                </td>
                              </tr>
                              {isExpanded && hasAnswers && (
                                <tr className="answers-expanded-row">
                                  <td colSpan={6}>
                                    <div className="answers-grid">
                                      {Object.entries(answers).map(([l, v]) => (
                                        <div key={l} className="answer-card">
                                          <span className="answer-question">{l}</span>
                                          <span className="answer-value">
                                            {Array.isArray(v) ? v.join(', ') : String(v)}
                                          </span>
                                        </div>
                                      ))}
                                    </div>
                                  </td>
                                </tr>
                              )}
                            </>
                          )
                        })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
