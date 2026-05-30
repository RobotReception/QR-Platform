/**
 * TemplateFieldMapping.tsx
 * 🎯 ربط حقول البيانات بمواقعها في القالب
 * - عرض معاينة للقالب
 * - تحديد مواقع الحقول (الاسم، التاريخ، الوقت، الباركود)
 * - التحقق من أن جميع الحقول محددة
 */

import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { templatesApi } from '../api/templatesApi'
import { CheckCircle2, AlertCircle, Eye, EyeOff, Zap } from 'lucide-react'
import './template-field-mapping.css'

interface TemplateField {
  element_type: string
  label?: string
  x: number
  y: number
  width: number
  height: number
  id: string
}

interface FieldMapping {
  guest_name?: string
  event_date?: string
  event_time?: string
  seat_number?: string
  barcode?: string
  qr_code?: string
}

interface TemplateFieldMappingProps {
  templateId: string
  eventId: string
  onMappingComplete: (mapping: FieldMapping) => void
  onCancel: () => void
}

export function TemplateFieldMapping({
  templateId,
  eventId,
  onMappingComplete,
  onCancel,
}: TemplateFieldMappingProps) {
  const [fieldMapping, setFieldMapping] = useState<FieldMapping>({})
  const [mappingErrors, setMappingErrors] = useState<string[]>([])
  const [showPreview, setShowPreview] = useState(true)

  // جلب تفاصيل القالب
  const { data: templateDetails, isLoading } = useQuery({
    queryKey: ['template-details', templateId],
    queryFn: async () => {
      // احصل على القالب مع عناصره
      const templates = await templatesApi.list(eventId)
      return templates.find((t) => t.id === templateId)
    },
  })

  // استخراج الحقول المتاحة من القالب
  const availableFields = extractFieldsFromTemplate(templateDetails)

  // التحقق من أن جميع الحقول المطلوبة محددة
  const validateMapping = (mapping: FieldMapping) => {
    const errors: string[] = []
    const requiredFields = ['guest_name', 'event_date', 'event_time', 'seat_number', 'barcode']

    for (const field of requiredFields) {
      if (!mapping[field as keyof FieldMapping]) {
        errors.push(`حقل مطلوب: ${getFieldLabel(field)}`)
      }
    }

    setMappingErrors(errors)
    return errors.length === 0
  }

  const handleFieldSelect = (fieldName: string, elementId: string) => {
    const newMapping = {
      ...fieldMapping,
      [fieldName]: elementId,
    }
    setFieldMapping(newMapping)
    validateMapping(newMapping)
  }

  const handleComplete = () => {
    if (validateMapping(fieldMapping)) {
      onMappingComplete(fieldMapping)
    }
  }

  if (isLoading) {
    return (
      <div className="template-field-mapping loading-state">
        <p>جاري تحميل تفاصيل القالب...</p>
      </div>
    )
  }

  if (!templateDetails) {
    return (
      <div className="template-field-mapping error-state">
        <AlertCircle size={48} />
        <p>لم يتم العثور على القالب</p>
      </div>
    )
  }

  return (
    <div className="template-field-mapping">
      <div className="mapping-header">
        <h3>🎯 ربط حقول البيانات مع القالب</h3>
        <p>حدد مكان كل حقل في قالب الدعوة</p>
      </div>

      <div className="mapping-container">
        {/* Preview Section */}
        <div className={`preview-section ${!showPreview ? 'hidden' : ''}`}>
          <div className="preview-header">
            <h4>معاينة القالب</h4>
            <button className="toggle-preview-btn" onClick={() => setShowPreview(!showPreview)}>
              {showPreview ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>

          <div className="template-preview">
            {templateDetails.background_url && (
              <div className="preview-background">
                <img src={templateDetails.background_url} alt="قالب" className="background-img" />

                {/* عرض العناصر على المعاينة */}
                <div className="elements-overlay">
                  {availableFields.map((field) => (
                    <div
                      key={field.id}
                      className={`field-indicator ${fieldMapping[getFieldDataKey(field.element_type)] === field.id ? 'selected' : ''}`}
                      style={{
                        left: `${field.x * 100}%`,
                        top: `${field.y * 100}%`,
                        width: `${field.width * 100}%`,
                        height: `${field.height * 100}%`,
                      }}
                      title={`${field.element_type}: ${field.label || 'بدون تسمية'}`}
                    >
                      <span className="field-label">{field.element_type}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {!templateDetails.background_url && (
              <div className="no-preview">
                <AlertCircle size={48} />
                <p>لا توجد صورة قالب</p>
              </div>
            )}
          </div>
        </div>

        {/* Mapping Section */}
        <div className="mapping-section">
          <div className="mapping-title">
            <h4>تعيين الحقول</h4>
            {mappingErrors.length === 0 && fieldMapping.guest_name && (
              <div className="progress-badge">
                <CheckCircle2 size={16} />
                {Object.keys(fieldMapping).length} / 5
              </div>
            )}
          </div>

          {/* الأخطاء */}
          {mappingErrors.length > 0 && (
            <div className="errors-box">
              {mappingErrors.map((error, i) => (
                <div key={i} className="error-item">
                  <AlertCircle size={14} />
                  {error}
                </div>
              ))}
            </div>
          )}

          {/* حقول التعيين */}
          <div className="fields-list">
            {getRequiredFields().map((field) => (
              <div key={field.key} className="field-item">
                <div className="field-info">
                  <label className="field-label">
                    {field.label}
                    {fieldMapping[field.key as keyof FieldMapping] && (
                      <CheckCircle2 size={14} className="check-icon" />
                    )}
                  </label>
                  <p className="field-description">{field.description}</p>
                </div>

                <div className="field-selector">
                  {availableFields.length === 0 ? (
                    <div className="no-fields">لا توجد حقول متاحة</div>
                  ) : (
                    <select
                      value={fieldMapping[field.key as keyof FieldMapping] || ''}
                      onChange={(e) => handleFieldSelect(field.key, e.target.value)}
                      className="field-select"
                    >
                      <option value="">-- اختر موقع الحقل --</option>
                      {availableFields.map((availField) => (
                        <option key={availField.id} value={availField.id}>
                          {availField.element_type}
                          {availField.label ? ` (${availField.label})` : ''}
                        </option>
                      ))}
                    </select>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* معلومات مفيدة */}
          <div className="info-box">
            <Zap size={16} />
            <p>
              <strong>نصيحة:</strong> تأكد من أن جميع الحقول محددة لضمان إنشاء دعوات صحيحة
            </p>
          </div>

          {/* الأزرار */}
          <div className="mapping-actions">
            <button className="btn btn-secondary" onClick={onCancel}>
              إلغاء
            </button>
            <button
              className="btn btn-primary"
              onClick={handleComplete}
              disabled={mappingErrors.length > 0}
            >
              <CheckCircle2 size={16} />
              تأكيد التعيين
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// Helper Functions
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

function extractFieldsFromTemplate(template: any): TemplateField[] {
  if (!template || !template.elements) return []

  return template.elements.map((elem: any) => ({
    id: elem.id,
    element_type: elem.element_type,
    label: elem.label,
    x: elem.x,
    y: elem.y,
    width: elem.width,
    height: elem.height,
  }))
}

function getFieldDataKey(elementType: string): string {
  const mapping: Record<string, string> = {
    guest_name: 'guest_name',
    event_date: 'event_date',
    event_time: 'event_time',
    seat_number: 'seat_number',
    barcode: 'barcode',
    qr_code: 'qr_code',
    custom_text: 'custom_text',
  }
  return mapping[elementType] || elementType
}

function getFieldLabel(field: string): string {
  const labels: Record<string, string> = {
    guest_name: 'اسم الضيف',
    event_date: 'التاريخ',
    event_time: 'الوقت',
    seat_number: 'رقم المقعد',
    barcode: 'الباركود',
    qr_code: 'كود QR',
  }
  return labels[field] || field
}

function getRequiredFields() {
  return [
    {
      key: 'guest_name',
      label: 'اسم الضيف',
      description: 'موقع إظهار اسم الضيف على الدعوة',
    },
    {
      key: 'event_date',
      label: 'التاريخ',
      description: 'موقع إظهار تاريخ الحفل',
    },
    {
      key: 'event_time',
      label: 'الوقت',
      description: 'موقع إظهار وقت الحفل',
    },
    {
      key: 'seat_number',
      label: 'رقم المقعد',
      description: 'موقع إظهار رقم المقعد',
    },
    {
      key: 'barcode',
      label: 'الباركود',
      description: 'موقع الباركود على الدعوة',
    },
  ]
}
