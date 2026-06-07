/**
 * useTemplatePreview.ts
 * Business logic for template preview and deletion.
 */
import { useMutation } from '@tanstack/react-query'
import http from '@services/http/client'
import type { InvitationStateReturn } from './useInvitationState'
import { EventModel } from '../../../types'

export function useTemplatePreview(state: InvitationStateReturn, event: EventModel) {
  const {
    selectedTemplateForPreview, setSelectedTemplateForPreview,
    setShowPreviewModal,
    setActivePreviewFields,
    previewData, setPreviewData,
    refetchTemplates,
  } = state

  // Delete template mutation
  const deleteMutation = useMutation({
    mutationFn: async (templateId: string) => {
      await http.delete(`/templates/${templateId}`)
    },
    onSuccess: () => {
      refetchTemplates()
    },
  })

  // Preview template mutation
  const previewMutation = useMutation({
    mutationFn: async ({ templateId, data }: { templateId: string; data: any }) => {
      const response = await http.post(
        `/templates/${templateId}/preview`,
        data,
        { responseType: 'blob' }
      )
      return URL.createObjectURL(response.data)
    },
  })

  // Map element to field descriptor
  const mapElementToField = (el: any) => {
    const etype = el.element_type
    const dk = el.data_key || ''

    if (etype === 'guest_name') {
      return { key: 'guest_name', label: 'اسم الضيف', type: 'text', defaultValue: 'أحمد علي' }
    }
    if (etype === 'event_title') {
      return { key: 'event_title', label: 'عنوان الحفل', type: 'text', defaultValue: event?.title || 'حفل تخرج' }
    }
    if (etype === 'event_date') {
      const parts = event?.start_date?.split('T') || []
      return { key: 'event_date', label: 'تاريخ الحفل', type: 'date', defaultValue: parts[0] || '2025-06-15' }
    }
    if (etype === 'event_time') {
      const parts = event?.start_date?.split('T') || []
      const defaultTime = parts[1] ? parts[1].substring(0, 5) : '19:00'
      return { key: 'event_time', label: 'وقت الحفل', type: 'time', defaultValue: defaultTime }
    }
    if (etype === 'event_location') {
      return { key: 'event_location', label: 'مكان الحفل', type: 'text', defaultValue: event?.venue_name || 'فندق الريتز' }
    }
    if (etype === 'seat_number') {
      return { key: 'seat_number', label: 'رقم المقعد', type: 'text', defaultValue: 'A12' }
    }
    if (etype === 'table_number') {
      return { key: 'table_number', label: 'رقم الطاولة', type: 'text', defaultValue: '5' }
    }
    if (etype === 'gate') {
      return { key: 'gate', label: 'البوابة', type: 'text', defaultValue: 'البوابة الرئيسية', isCustomData: true, customKey: 'gate' }
    }
    if (etype === 'hall') {
      return { key: 'hall', label: 'القاعة', type: 'text', defaultValue: 'القاعة الكبرى', isCustomData: true, customKey: 'hall' }
    }

    if (etype === 'dynamic_text' && dk) {
      const keyNorm = dk.trim().toLowerCase()

      if (['guest.name', 'guest.name_ar', 'guest_name', 'name', 'الاسم', 'اسم الضيف', 'guestname', 'اسم_الضيف'].includes(keyNorm)) {
        return { key: 'guest_name', label: 'اسم الضيف', type: 'text', defaultValue: 'أحمد علي' }
      }
      if (['guest.phone', 'guest_phone', 'phone', 'الجوال', 'رقم الجوال', 'رقم الهاتف', 'الهاتف'].includes(keyNorm)) {
        return { key: 'guest_phone', label: 'رقم الجوال', type: 'text', defaultValue: '0500000000' }
      }
      if (['guest.email', 'guest_email', 'email', 'البريد', 'البريد الإلكتروني'].includes(keyNorm)) {
        return { key: 'guest_email', label: 'البريد الإلكتروني', type: 'text', defaultValue: 'guest@example.com' }
      }
      if (['guest.company', 'guest_company', 'company', 'الجهة', 'الجهة / الشركة', 'الشركة', 'جهة العمل'].includes(keyNorm)) {
        return { key: 'guest_company', label: 'الجهة / الشركة', type: 'text', defaultValue: 'شركة التقنية' }
      }
      if (['guest.title', 'guest_title', 'title', 'المسمى الوظيفي', 'المنصب'].includes(keyNorm)) {
        return { key: 'guest_title', label: 'المسمى الوظيفي', type: 'text', defaultValue: 'مدير عام' }
      }
      if (['event.title', 'event.title_ar', 'event_title', 'title', 'العنوان', 'اسم الفعالية', 'عنوان الفعالية'].includes(keyNorm)) {
        return { key: 'event_title', label: 'عنوان الحفل', type: 'text', defaultValue: event?.title || 'حفل تخرج' }
      }
      if (['event.date', 'event_date', 'date', 'التاريخ', 'تاريخ', 'تاريخ الفعالية'].includes(keyNorm)) {
        const parts = event?.start_date?.split('T') || []
        return { key: 'event_date', label: 'تاريخ الحفل', type: 'date', defaultValue: parts[0] || '2025-06-15' }
      }
      if (['event.time', 'event_time', 'time', 'الوقت', 'وقت', 'وقت الفعالية'].includes(keyNorm)) {
        const parts = event?.start_date?.split('T') || []
        const defaultTime = parts[1] ? parts[1].substring(0, 5) : '19:00'
        return { key: 'event_time', label: 'وقت الحفل', type: 'time', defaultValue: defaultTime }
      }
      if (['event.location', 'event.location_ar', 'event_location', 'location', 'المكان', 'الموقع', 'venue'].includes(keyNorm)) {
        return { key: 'event_location', label: 'مكان الحفل', type: 'text', defaultValue: event?.venue_name || 'فندق الريتز' }
      }
      if (['custom.seat', 'seat_number', 'seat', 'رقم المقعد', 'المقعد'].includes(keyNorm)) {
        return { key: 'seat_number', label: 'رقم المقعد', type: 'text', defaultValue: 'A12' }
      }
      if (['custom.table', 'table_number', 'table', 'الطاولة', 'رقم الطاولة'].includes(keyNorm)) {
        return { key: 'table_number', label: 'رقم الطاولة', type: 'text', defaultValue: '5' }
      }
      if (['custom.gate', 'gate', 'البوابة', 'بوابة'].includes(keyNorm)) {
        return { key: 'gate', label: 'البوابة', type: 'text', defaultValue: 'البوابة الرئيسية', isCustomData: true, customKey: 'gate' }
      }
      if (['custom.hall', 'hall', 'القاعة', 'قاعة'].includes(keyNorm)) {
        return { key: 'hall', label: 'القاعة', type: 'text', defaultValue: 'القاعة الكبرى', isCustomData: true, customKey: 'hall' }
      }

      const cleanKey = dk.startsWith('custom.') ? dk.substring(7) : dk
      const fieldLabel = el.label || cleanKey
      return {
        key: `custom_data.${cleanKey}`,
        label: fieldLabel,
        type: 'text',
        defaultValue: `بيانات ${fieldLabel}`,
        isCustomData: true,
        customKey: cleanKey
      }
    }
    return null
  }

  const detectFields = (elements: any[]) => {
    const fieldsMap = new Map<string, any>()
    for (const el of elements) {
      const field = mapElementToField(el)
      if (field && !fieldsMap.has(field.key)) {
        fieldsMap.set(field.key, field)
      }
    }
    return Array.from(fieldsMap.values())
  }

  const handlePreview = async (template: any) => {
    setSelectedTemplateForPreview(template)
    try {
      const elements = await import('../../../api/templatesApi').then(m => m.templatesApi.getElements(template.id))
      const fields = detectFields(elements)
      setActivePreviewFields(fields)

      const initialData: any = {
        guest_name: '', guest_phone: '', guest_email: '',
        guest_company: '', guest_title: '',
        event_title: '', event_date: '', event_time: '',
        event_location: '',
        seat_number: '', table_number: '',
        custom_data: {},
      }

      fields.forEach((f) => {
        if (f.isCustomData) {
          initialData.custom_data[f.customKey] = f.defaultValue
        } else {
          initialData[f.key] = f.defaultValue
        }
      })

      setPreviewData(initialData)
      setShowPreviewModal(true)
      await previewMutation.mutateAsync({ templateId: template.id, data: initialData })
    } catch (err) {
      console.error('Failed to load preview:', err)
      alert('فشل تحميل تفاصيل القالب للمعاينة')
    }
  }

  const handleDeleteTemplate = (template: any) => {
    if (window.confirm(`هل أنت متأكد من حذف القالب "${template.name}"؟`)) {
      setSelectedTemplateForPreview(template)
      deleteMutation.mutate(template.id)
    }
  }

  const handleDownloadPreview = async () => {
    if (!selectedTemplateForPreview) return
    try {
      const response = await http.post(
        `/templates/${selectedTemplateForPreview.id}/preview`,
        previewData,
        { responseType: 'blob' }
      )
      const blob = response.data
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `preview_${selectedTemplateForPreview.name || 'template'}.png`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Failed to download preview image:', err)
      alert('فشل تحميل المعاينة')
    }
  }

  return {
    handlePreview,
    handleDeleteTemplate,
    handleDownloadPreview,
    previewMutation,
    deleteMutation,
    mapElementToField,
    detectFields,
  }
}
