/**
 * TemplateSelectionFlow.tsx - محسّن مع اختيار نوع الدعوات
 * 🎯 نظام احترافي وسلس لاختيار نوع الدعوات ثم القالب
 *
 * الخطوات الجديدة:
 * - اختيار نوع الدعوات (VIP / Normal)
 * - اختيار القالب (مُصفى حسب النوع)
 * - تحميل ملف Excel
 * - تعيين البيانات
 * - معاينة النتائج
 */

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useAuthStore } from '@features/auth/store/authStore'
import { templatesApi } from '../api/templatesApi'
import {
  Upload, CheckCircle2, AlertCircle, ChevronRight, ChevronLeft,
  Loader2, Download, Eye, X, Crown, Users
} from 'lucide-react'
import * as XLSX from 'xlsx'
import './template-selection-flow.css'

interface TemplateSelectionFlowProps {
  eventId: string
  onComplete: (data: {
    invitationType: 'vip' | 'normal'
    templateId: string
    templateName: string
    guests: Array<{
      guest_name: string
      event_date: string
      event_time: string
      seat_number: string
      [key: string]: string
    }>
    columnMapping: Record<string, string>
  }) => void
  onCancel: () => void
}

type Step = 'type' | 'template' | 'upload' | 'mapping' | 'preview'
type InvitationType = 'vip' | 'normal'

interface ExcelColumn {
  name: string
  index: number
  sampleValues: string[]
}

interface InvitationTypeOption {
  id: InvitationType
  label: string
  description: string
  icon: React.ReactNode
  color: string
  borderColor: string
}

export function TemplateSelectionFlow({ eventId, onComplete, onCancel }: TemplateSelectionFlowProps) {
  const [currentStep, setCurrentStep] = useState<Step>('type')
  const [invitationType, setInvitationType] = useState<InvitationType | null>(null)
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>('')
  const [selectedTemplateName, setSelectedTemplateName] = useState<string>('')
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [excelColumns, setExcelColumns] = useState<ExcelColumn[]>([])
  const [excelRows, setExcelRows] = useState<Record<string, string>[]>([])
  const [columnMapping, setColumnMapping] = useState<Record<string, string>>({})
  const [mappingErrors, setMappingErrors] = useState<string[]>([])
  const [isProcessing, setIsProcessing] = useState(false)

  const { user } = useAuthStore()

  // جلب القوالب كلها
  const { data: allTemplates = [], isLoading: isLoadingTemplates } = useQuery({
    queryKey: ['templates', eventId],
    queryFn: () => templatesApi.list(eventId),
  })

  // تصفية القوالب بناءً على النوع المختار
  const templates = invitationType
    ? allTemplates.filter((t) => t.type === invitationType || !t.type)
    : []

  const invitationTypes: InvitationTypeOption[] = [
    {
      id: 'vip',
      label: '👑 دعوات VIP',
      description: 'دعوات فاخرة مميزة للضيوف المهمين',
      icon: <Crown size={48} />,
      color: 'from-yellow-400 to-yellow-600',
      borderColor: 'border-yellow-300',
    },
    {
      id: 'normal',
      label: '👥 دعوات عادية',
      description: 'دعوات عادية للضيوف العاديين',
      icon: <Users size={48} />,
      color: 'from-blue-400 to-blue-600',
      borderColor: 'border-blue-300',
    },
  ]

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // الخطوة 1: اختيار نوع الدعوات
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  const handleTypeSelect = (type: InvitationType) => {
    setInvitationType(type)
    setCurrentStep('template')
  }

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // الخطوة 2: اختيار القالب
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  const handleTemplateSelect = (templateId: string, templateName: string) => {
    setSelectedTemplateId(templateId)
    setSelectedTemplateName(templateName)
  }

  const handleTemplateNext = () => {
    if (!selectedTemplateId) {
      alert('يرجى اختيار قالب')
      return
    }
    setCurrentStep('upload')
  }

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // الخطوة 3: تحميل الملف
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  const handleFileUpload = async (file: File) => {
    if (!file) return

    setUploadedFile(file)
    setIsProcessing(true)

    try {
      const arrayBuffer = await file.arrayBuffer()
      const workbook = XLSX.read(arrayBuffer, { type: 'array' })
      const worksheet = workbook.Sheets[workbook.SheetNames[0]]
      const data = XLSX.utils.sheet_to_json<Record<string, string>>(worksheet)

      if (data.length === 0) {
        alert('الملف فارغ')
        return
      }

      const columnNames = Object.keys(data[0])
      const columns: ExcelColumn[] = columnNames.map((name, index) => ({
        name,
        index,
        sampleValues: data.slice(0, 3).map((row) => row[name] || ''),
      }))

      setExcelColumns(columns)
      setExcelRows(data)

      // محاولة استخراج البيانات تلقائياً
      autoDetectMapping(columns)

      setCurrentStep('mapping')
    } catch (error) {
      alert(`خطأ في قراءة الملف: ${error instanceof Error ? error.message : 'خطأ غير معروف'}`)
    } finally {
      setIsProcessing(false)
    }
  }

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // الاستخراج التلقائي للبيانات
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  const autoDetectMapping = (columns: ExcelColumn[]) => {
    const mapping: Record<string, string> = {}
    const requiredFields = ['guest_name', 'event_date', 'event_time', 'seat_number']

    for (const field of requiredFields) {
      const columnName = findMatchingColumn(field, columns)
      if (columnName) {
        mapping[field] = columnName
      }
    }

    setColumnMapping(mapping)
    validateMapping(mapping, requiredFields)
  }

  const findMatchingColumn = (field: string, columns: ExcelColumn[]): string | null => {
    const fieldLower = field.toLowerCase()
    const aliases: Record<string, string[]> = {
      guest_name: ['اسم الضيف', 'guest_name', 'name', 'اسم', 'الاسم', 'guestname'],
      event_date: ['تاريخ', 'event_date', 'date', 'التاريخ', 'eventdate'],
      event_time: ['وقت', 'event_time', 'time', 'الوقت', 'eventtime'],
      seat_number: ['مقعد', 'seat_number', 'seat', 'رقم المقعد', 'seatnumber'],
    }

    const potentialMatches = aliases[field] || []

    // ابحث عن تطابق دقيق أولاً
    for (const col of columns) {
      const colLower = col.name.toLowerCase()
      if (potentialMatches.some((alias) => colLower === alias.toLowerCase())) {
        return col.name
      }
    }

    // ابحث عن تطابق جزئي
    for (const col of columns) {
      const colLower = col.name.toLowerCase()
      if (potentialMatches.some((alias) => colLower.includes(alias.toLowerCase()) || alias.toLowerCase().includes(colLower))) {
        return col.name
      }
    }

    return null
  }

  const validateMapping = (mapping: Record<string, string>, requiredFields: string[]) => {
    const errors: string[] = []

    for (const field of requiredFields) {
      if (!mapping[field]) {
        errors.push(`حقل مطلوب: ${getFieldLabel(field)}`)
      }
    }

    setMappingErrors(errors)
  }

  const getFieldLabel = (field: string): string => {
    const labels: Record<string, string> = {
      guest_name: 'اسم الضيف',
      event_date: 'التاريخ',
      event_time: 'الوقت',
      seat_number: 'رقم المقعد',
    }
    return labels[field] || field
  }

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // الخطوة 4: تعديل التعيين
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  const handleMappingChange = (field: string, columnName: string) => {
    const newMapping = { ...columnMapping, [field]: columnName }
    setColumnMapping(newMapping)

    const requiredFields = ['guest_name', 'event_date', 'event_time', 'seat_number']
    validateMapping(newMapping, requiredFields)
  }

  const handleMappingNext = () => {
    if (mappingErrors.length > 0) {
      alert('يرجى ملء جميع الحقول المطلوبة')
      return
    }
    setCurrentStep('preview')
  }

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // الخطوة 5: المعاينة والتأكيد
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  const getPreviewData = () => {
    return excelRows.slice(0, 5).map((row) => ({
      guest_name: row[columnMapping.guest_name] || '',
      event_date: row[columnMapping.event_date] || '',
      event_time: row[columnMapping.event_time] || '',
      seat_number: row[columnMapping.seat_number] || '',
    }))
  }

  const handleComplete = () => {
    if (!invitationType) {
      alert('يرجى اختيار نوع الدعوات')
      return
    }

    const guests = excelRows.map((row) => ({
      guest_name: row[columnMapping.guest_name] || '',
      event_date: row[columnMapping.event_date] || '',
      event_time: row[columnMapping.event_time] || '',
      seat_number: row[columnMapping.seat_number] || '',
      ...row,
    }))

    onComplete({
      invitationType,
      templateId: selectedTemplateId,
      templateName: selectedTemplateName,
      guests,
      columnMapping,
    })
  }

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // واجهة المستخدم
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  return (
    <div className="template-selection-flow">
      <div className="flow-header">
        <h2>🎯 إنشاء دعوات احترافية</h2>
        <p className="flow-subtitle">عملية احترافية وسلسة مع اختيار نوع الدعوات</p>
      </div>

      {/* Progress Bar - 5 خطوات */}
      <div className="flow-progress">
        <div className={`progress-step ${currentStep === 'type' ? 'active' : ['template', 'upload', 'mapping', 'preview'].includes(currentStep) ? 'completed' : ''}`}>
          <div className="step-number">1</div>
          <div className="step-label">نوع الدعوات</div>
        </div>
        <div className="progress-line" />
        <div className={`progress-step ${currentStep === 'template' ? 'active' : ['upload', 'mapping', 'preview'].includes(currentStep) ? 'completed' : ''}`}>
          <div className="step-number">2</div>
          <div className="step-label">اختيار القالب</div>
        </div>
        <div className="progress-line" />
        <div className={`progress-step ${currentStep === 'upload' ? 'active' : ['mapping', 'preview'].includes(currentStep) ? 'completed' : ''}`}>
          <div className="step-number">3</div>
          <div className="step-label">تحميل الملف</div>
        </div>
        <div className="progress-line" />
        <div className={`progress-step ${currentStep === 'mapping' ? 'active' : currentStep === 'preview' ? 'completed' : ''}`}>
          <div className="step-number">4</div>
          <div className="step-label">تعيين البيانات</div>
        </div>
        <div className="progress-line" />
        <div className={`progress-step ${currentStep === 'preview' ? 'active' : ''}`}>
          <div className="step-number">5</div>
          <div className="step-label">معاينة</div>
        </div>
      </div>

      {/* Flow Content */}
      <div className="flow-content">
        {/* Step 0: Invitation Type Selection */}
        {currentStep === 'type' && (
          <div className="flow-step type-selection-step">
            <div className="step-title">اختر نوع الدعوات</div>
            <p className="step-description">حدد نوع الدعوات التي تريد إنشاءها</p>

            <div className="invitation-types-grid">
              {invitationTypes.map((type) => (
                <div
                  key={type.id}
                  className={`invitation-type-card ${invitationType === type.id ? 'selected' : ''}`}
                  onClick={() => handleTypeSelect(type.id)}
                >
                  <div className={`type-icon bg-gradient-to-br ${type.color}`}>
                    {type.icon}
                  </div>
                  <h3 className="type-label">{type.label}</h3>
                  <p className="type-description">{type.description}</p>
                  {invitationType === type.id && (
                    <div className="selection-indicator">
                      <CheckCircle2 size={20} />
                    </div>
                  )}
                </div>
              ))}
            </div>

            <div className="step-actions">
              <button className="btn btn-secondary" onClick={onCancel}>
                <X size={16} />
                إغلاق
              </button>
              <button className="btn btn-primary" onClick={() => handleTypeSelect(invitationType!)} disabled={!invitationType}>
                التالي
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        )}

        {/* Step 1: Template Selection */}
        {currentStep === 'template' && (
          <div className="flow-step template-selection-step">
            <div className="step-title">
              اختر القالب {invitationType === 'vip' ? '👑 (VIP)' : '👥 (عادي)'}
            </div>
            <p className="step-description">اختر القالب المناسب للدعوات</p>

            {isLoadingTemplates ? (
              <div className="loading-state">
                <Loader2 size={32} className="spin" />
                <p>جاري تحميل القوالب...</p>
              </div>
            ) : templates.length === 0 ? (
              <div className="empty-state">
                <AlertCircle size={48} />
                <p>لا توجد قوالب متاحة لهذا النوع</p>
              </div>
            ) : (
              <div className="templates-grid">
                {templates.map((template) => (
                  <div
                    key={template.id}
                    className={`template-option ${selectedTemplateId === template.id ? 'selected' : ''}`}
                    onClick={() => handleTemplateSelect(template.id, template.name)}
                  >
                    {template.background_url && (
                      <img src={template.background_url} alt={template.name} className="template-thumbnail" />
                    )}
                    <div className="template-info">
                      <h4 className="template-name">{template.name}</h4>
                      <p className="template-type">{template.type || 'بدون تصنيف'}</p>
                    </div>
                    {selectedTemplateId === template.id && (
                      <div className="selection-indicator">
                        <CheckCircle2 size={24} />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            <div className="step-actions">
              <button className="btn btn-secondary" onClick={() => setCurrentStep('type')}>
                <ChevronLeft size={16} />
                رجوع
              </button>
              <button className="btn btn-primary" onClick={handleTemplateNext} disabled={!selectedTemplateId}>
                التالي
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        )}

        {/* Step 2: File Upload */}
        {currentStep === 'upload' && (
          <div className="flow-step file-upload-step">
            <div className="step-title">تحميل ملف البيانات</div>
            <p className="step-description">حمّل ملف Excel يحتوي على بيانات الضيوف</p>

            <div className="file-upload-area">
              <input
                id="file-input"
                type="file"
                accept=".xlsx,.csv"
                onChange={(e) => e.target.files && handleFileUpload(e.target.files[0])}
              />
              <label htmlFor="file-input" className={`upload-label ${uploadedFile ? 'has-file' : ''}`}>
                {isProcessing ? (
                  <>
                    <Loader2 size={32} className="spin" />
                    <p>جاري معالجة الملف...</p>
                  </>
                ) : uploadedFile ? (
                  <>
                    <CheckCircle2 size={32} />
                    <p>{uploadedFile.name}</p>
                    <span className="upload-hint">انقر لاختيار ملف آخر</span>
                  </>
                ) : (
                  <>
                    <Upload size={32} />
                    <p>اسحب الملف هنا أو انقر للاختيار</p>
                    <span className="upload-hint">ملفات Excel (.xlsx) أو CSV (.csv)</span>
                  </>
                )}
              </label>
            </div>

            <div className="template-hint">
              <div className="hint-title">📋 تنسيق الملف المطلوب:</div>
              <table className="format-table">
                <thead>
                  <tr>
                    <th>الحقل</th>
                    <th>الوصف</th>
                    <th>مثال</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>اسم الضيف</td>
                    <td>اسم الضيف أو الجهة</td>
                    <td>أحمد محمد</td>
                  </tr>
                  <tr>
                    <td>التاريخ</td>
                    <td>تاريخ الحفل (YYYY-MM-DD)</td>
                    <td>2025-06-15</td>
                  </tr>
                  <tr>
                    <td>الوقت</td>
                    <td>وقت الحفل (HH:MM)</td>
                    <td>19:00</td>
                  </tr>
                  <tr>
                    <td>رقم المقعد</td>
                    <td>رقم المقعد أو الموقع</td>
                    <td>A12</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div className="step-actions">
              <button className="btn btn-secondary" onClick={() => setCurrentStep('template')}>
                <ChevronLeft size={16} />
                رجوع
              </button>
              <button className="btn btn-primary" onClick={() => setCurrentStep('mapping')} disabled={!uploadedFile}>
                التالي
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Column Mapping */}
        {currentStep === 'mapping' && (
          <div className="flow-step mapping-step">
            <div className="step-title">تعيين الأعمدة</div>
            <p className="step-description">تحقق من تعيين الأعمدة تلقائياً أو عدّلها حسب الحاجة</p>

            {mappingErrors.length > 0 && (
              <div className="error-box">
                {mappingErrors.map((error, i) => (
                  <div key={i} className="error-item">
                    <AlertCircle size={16} />
                    {error}
                  </div>
                ))}
              </div>
            )}

            <div className="mapping-container">
              {['guest_name', 'event_date', 'event_time', 'seat_number'].map((field) => (
                <div key={field} className="mapping-item">
                  <label className="mapping-label">
                    {getFieldLabel(field)}
                    {columnMapping[field] && <CheckCircle2 size={16} className="check-icon" />}
                  </label>
                  <select
                    value={columnMapping[field] || ''}
                    onChange={(e) => handleMappingChange(field, e.target.value)}
                    className="mapping-select"
                  >
                    <option value="">-- اختر عمود --</option>
                    {excelColumns.map((col) => (
                      <option key={col.name} value={col.name}>
                        {col.name} {col.sampleValues[0] ? `(مثال: ${col.sampleValues[0]})` : ''}
                      </option>
                    ))}
                  </select>
                </div>
              ))}
            </div>

            <div className="step-actions">
              <button className="btn btn-secondary" onClick={() => setCurrentStep('upload')}>
                <ChevronLeft size={16} />
                رجوع
              </button>
              <button
                className="btn btn-primary"
                onClick={handleMappingNext}
                disabled={mappingErrors.length > 0}
              >
                معاينة النتائج
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        )}

        {/* Step 4: Preview */}
        {currentStep === 'preview' && (
          <div className="flow-step preview-step">
            <div className="step-title">معاينة النتائج</div>
            <p className="step-description">تحقق من البيانات قبل إنشاء الدعوات ({excelRows.length} ضيف)</p>

            <div className="preview-container">
              <div className="preview-header">
                <div className="template-info">
                  <strong>القالب:</strong> {selectedTemplateName}
                </div>
                <div className="invitation-type-info">
                  <strong>النوع:</strong> {invitationType === 'vip' ? '👑 VIP' : '👥 عادي'}
                </div>
                <div className="guest-count">
                  <strong>عدد الضيوف:</strong> {excelRows.length}
                </div>
              </div>

              <div className="preview-table-wrapper">
                <table className="preview-table">
                  <thead>
                    <tr>
                      <th>اسم الضيف</th>
                      <th>التاريخ</th>
                      <th>الوقت</th>
                      <th>المقعد</th>
                    </tr>
                  </thead>
                  <tbody>
                    {getPreviewData().map((row, idx) => (
                      <tr key={idx}>
                        <td>{row.guest_name}</td>
                        <td>{row.event_date}</td>
                        <td>{row.event_time}</td>
                        <td>{row.seat_number}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {excelRows.length > 5 && (
                <div className="more-rows-hint">
                  ... و {excelRows.length - 5} ضيف آخر
                </div>
              )}
            </div>

            <div className="step-actions">
              <button className="btn btn-secondary" onClick={() => setCurrentStep('mapping')}>
                <ChevronLeft size={16} />
                رجوع
              </button>
              <button className="btn btn-success" onClick={handleComplete}>
                <CheckCircle2 size={16} />
                إنشاء الدعوات
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
