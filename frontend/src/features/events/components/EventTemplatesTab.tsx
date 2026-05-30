/**
 * EventTemplatesTab.tsx
 * إدارة القوالب المخصصة للحدث - إضافة، معاينة، حذف
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import http from '@services/http/client'
import { Plus, Eye, Trash2, Download, AlertCircle, Loader2, Pencil } from 'lucide-react'
import { useAuthStore } from '@features/auth/store/authStore'
import { templatesApi } from '@features/events/api/templatesApi'
import './EventTemplatesTab.css'

interface EventTemplatesTabProps {
  eventId: string
  isActiveTab: boolean
}

export function EventTemplatesTab({ eventId, isActiveTab }: EventTemplatesTabProps) {
  const navigate = useNavigate()
  const [selectedTemplate, setSelectedTemplate] = useState<any>(null)
  const [showPreviewModal, setShowPreviewModal] = useState(false)
  const [previewData, setPreviewData] = useState({
    guest_name: 'أحمد علي',
    event_title: 'حفل تخرج',
    event_date: '2025-06-15',
    event_time: '19:00',
    event_location: 'فندق الريتز',
    seat_number: 'A12',
    table_number: '5',
  })

  const tenantId = useAuthStore((s) => s.currentTenantId)

  // جلب القوالب الخاصة بالحدث
  const { data: templates, isLoading, refetch } = useQuery({
    queryKey: ['templates', eventId, tenantId],
    queryFn: async () => {
      if (!isActiveTab || !tenantId) return []
      return templatesApi.list(eventId)
    },
    enabled: isActiveTab && !!tenantId,
  })

  // حذف القالب
  const deleteMutation = useMutation({
    mutationFn: async (templateId: string) => {
      await http.delete(`/templates/${templateId}`)
    },
    onSuccess: () => {
      refetch()
    },
  })

  // معاينة القالب
  const previewMutation = useMutation({
    mutationFn: async (templateId: string) => {
      const response = await http.post(
        `/templates/${templateId}/preview`,
        previewData,
        {
          responseType: 'blob',
        }
      )
      return URL.createObjectURL(response.data)
    },
  })

  const handlePreview = async (template: any) => {
    setSelectedTemplate(template)
    await previewMutation.mutateAsync(template.id)
    setShowPreviewModal(true)
  }

  const handleDelete = (template: any) => {
    if (window.confirm(`هل أنت متأكد من حذف القالب "${template.name}"؟`)) {
      deleteMutation.mutate(template.id)
    }
  }

  const handleDownloadPreview = async () => {
    if (!selectedTemplate) return
    await previewMutation.mutateAsync(selectedTemplate.id)
    // The preview is already loaded in previewMutation.data
  }

  if (isLoading) {
    return (
      <div className="event-templates-loading">
        <Loader2 size={32} className="spin" />
        <p>جاري تحميل القوالب...</p>
      </div>
    )
  }

  return (
    <div className="event-templates-tab">
      {/* Header */}
      <div className="templates-header">
        <div>
          <h2>قوالب الحدث</h2>
          <p className="templates-subtitle">
            إدارة القوالب المخصصة للدعوات - إضافة، معاينة، وحذف
          </p>
        </div>
        <button className="btn btn-primary">
          <Plus size={16} />
          قالب جديد
        </button>
      </div>

      {/* Templates Grid */}
      {!templates || templates.length === 0 ? (
        <div className="templates-empty-state">
          <AlertCircle size={48} />
          <h3>لا توجد قوالب</h3>
          <p>أنشئ قالب جديد لبدء تخصيص دعوات الحدث</p>
          <button className="btn btn-primary">
            <Plus size={16} />
            إنشاء قالب جديد
          </button>
        </div>
      ) : (
        <div className="templates-grid">
          {templates.map((template: any) => (
            <div key={template.id} className="template-card">
              {/* Thumbnail */}
              <div className="template-thumbnail">
                {template.background_url ? (
                  <img
                    src={template.background_url}
                    alt={template.name}
                    className="template-image"
                  />
                ) : (
                  <div className="template-placeholder">
                    <span>لا توجد صورة</span>
                  </div>
                )}
              </div>

              {/* Template Info */}
              <div className="template-info">
                <h3 title={template.name}>{template.name}</h3>
                <p className="template-type">
                  {template.template_type === 'designed' ? '🎨 مصمم' : '⚡ سريع'}
                </p>
                {template.width_px && template.height_px && (
                  <p className="template-size">
                    {template.width_px} × {template.height_px} px
                  </p>
                )}
              </div>

              {/* Actions */}
              <div className="template-actions">
                <button
                  className="action-btn edit-btn"
                  onClick={() => navigate(`/events/${eventId}/design?edit=${template.id}`)}
                  title="تحرير التصميم"
                >
                  <Pencil size={16} />
                </button>
                <button
                  className="action-btn preview-btn"
                  onClick={() => handlePreview(template)}
                  title="معاينة"
                  disabled={previewMutation.isPending}
                >
                  {previewMutation.isPending && selectedTemplate?.id === template.id ? (
                    <Loader2 size={16} className="spin" />
                  ) : (
                    <Eye size={16} />
                  )}
                </button>
                <button
                  className="action-btn download-btn"
                  onClick={handleDownloadPreview}
                  title="تحميل المعاينة"
                  disabled={!selectedTemplate || previewMutation.isPending}
                >
                  <Download size={16} />
                </button>
                <button
                  className="action-btn delete-btn"
                  onClick={() => handleDelete(template)}
                  title="حذف"
                  disabled={deleteMutation.isPending}
                >
                  {deleteMutation.isPending ? (
                    <Loader2 size={16} className="spin" />
                  ) : (
                    <Trash2 size={16} />
                  )}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Preview Modal */}
      {showPreviewModal && (
        <div className="preview-modal-overlay" onClick={() => setShowPreviewModal(false)}>
          <div className="preview-modal" onClick={e => e.stopPropagation()}>
            <div className="preview-modal-header">
              <h2>معاينة القالب - {selectedTemplate?.name}</h2>
              <button
                className="close-btn"
                onClick={() => setShowPreviewModal(false)}
              >
                ✕
              </button>
            </div>

            <div className="preview-modal-content">
              {/* Preview Image */}
              <div className="preview-image-container">
                {previewMutation.data ? (
                  <img
                    src={previewMutation.data}
                    alt="معاينة"
                    className="preview-image"
                  />
                ) : (
                  <div className="preview-loading">
                    <Loader2 size={32} className="spin" />
                    <p>جاري تحضير المعاينة...</p>
                  </div>
                )}
              </div>

              {/* Preview Data Editor */}
              <div className="preview-data-editor">
                <h3>بيانات الاختبار</h3>
                <div className="preview-form">
                  <div className="form-group">
                    <label>اسم الضيف</label>
                    <input
                      type="text"
                      value={previewData.guest_name}
                      onChange={e => setPreviewData({ ...previewData, guest_name: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label>عنوان الحفل</label>
                    <input
                      type="text"
                      value={previewData.event_title}
                      onChange={e => setPreviewData({ ...previewData, event_title: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label>التاريخ</label>
                    <input
                      type="date"
                      value={previewData.event_date}
                      onChange={e => setPreviewData({ ...previewData, event_date: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label>الوقت</label>
                    <input
                      type="time"
                      value={previewData.event_time}
                      onChange={e => setPreviewData({ ...previewData, event_time: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label>المكان</label>
                    <input
                      type="text"
                      value={previewData.event_location}
                      onChange={e => setPreviewData({ ...previewData, event_location: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label>رقم المقعد</label>
                    <input
                      type="text"
                      value={previewData.seat_number}
                      onChange={e => setPreviewData({ ...previewData, seat_number: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label>رقم الطاولة</label>
                    <input
                      type="text"
                      value={previewData.table_number}
                      onChange={e => setPreviewData({ ...previewData, table_number: e.target.value })}
                    />
                  </div>

                  <button
                    className="btn btn-secondary"
                    onClick={() => previewMutation.mutate(selectedTemplate?.id!)}
                    disabled={previewMutation.isPending}
                  >
                    {previewMutation.isPending ? (
                      <>
                        <Loader2 size={14} className="spin" />
                        جاري التحديث...
                      </>
                    ) : (
                      'تحديث المعاينة'
                    )}
                  </button>
                </div>
              </div>
            </div>

            <div className="preview-modal-footer">
              <button
                className="btn btn-secondary"
                onClick={() => setShowPreviewModal(false)}
              >
                إغلاق
              </button>
              <button
                className="btn btn-primary"
                onClick={handleDownloadPreview}
              >
                <Download size={16} />
                تحميل المعاينة
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
