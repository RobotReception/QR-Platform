import { useEffect, useState, useMemo } from 'react'
import { useQuery, useQueries, useMutation } from '@tanstack/react-query'
import { useNavigate, useSearchParams } from 'react-router-dom'
import * as XLSX from 'xlsx'
import http from '@services/http/client'
import { EventModel, EventStats } from '../types'
import { useGenerateInvitations } from '../hooks/useGenerateInvitations'
import { DEFAULT_LAYOUT, type LayoutConfig } from '../api/invitationsApi'
import { invitationsAPI } from '@features/invitations/api/invitationsApi'
import { batchesApi, type BatchLayoutConfig } from '../api/batchesApi'
import { templatesApi } from '../api/templatesApi'
// TemplateSelectionFlow is available for the professional flow modal
import {
  Printer, Download, Users, Loader2, Sparkles,
  Settings2, Grid3X3, ChevronDown, ChevronUp, Eye, EyeOff,
  CheckCircle2, AlertCircle, Upload, FileSpreadsheet, X, Plus, QrCode, Database,
  Pencil, Trash2,
} from 'lucide-react'
import './EventTemplatesTab.css'
import '../pages/events.css'

interface Props {
  event: EventModel
  stats?: EventStats
}

const GRID_PRESETS = [
  { label: '3×3', rows: 3, cols: 3 },
  { label: '4×4', rows: 4, cols: 4 },
  { label: '5×5', rows: 5, cols: 5 },
  { label: '4×6', rows: 6, cols: 4 },
  { label: '5×8', rows: 8, cols: 5 },
]

const BARCODE_SIZES = [
  { label: 'تلقائي', value: null },
  { label: '200px', value: 200 },
  { label: '300px', value: 300 },
  { label: '400px', value: 400 },
  { label: '500px', value: 500 },
  { label: '600px', value: 600 },
]

type GuestImportRow = {
  guest_name: string
  invitation_count: number
  ticket_class: 'vip' | 'normal'
  custom_fields?: Record<string, string>
}

const TEMPLATE_ROWS = [
  { 'اسم الضيف': 'أحمد محمد', 'عدد الأشخاص': 2, 'نوع التذكرة': 'normal' },
  { 'اسم الضيف': 'شركة النور', 'عدد الأشخاص': 5, 'نوع التذكرة': 'vip' },
]

const TEMPLATE_GUIDE_ROWS = [
  { 'Ø§Ù„Ø­Ù‚Ù„': 'Ø§Ø³Ù… Ø§Ù„Ø¶ÙŠÙ ', 'Ø§Ù„ÙˆØµÙ ': 'Ø§Ø³Ù… Ø§Ù„Ø¶ÙŠÙ  Ø£Ùˆ Ø§Ù„Ø¬Ù‡Ø© Ø§Ù„Ù…Ø¯Ø¹ÙˆØ©', 'Ù…Ø·Ù„ÙˆØ¨': 'Ù†Ø¹Ù…', 'Ù…Ø«Ø§Ù„': 'Ø£Ø­Ù…Ø¯ Ù…Ø­Ù…Ø¯' },
  { 'Ø§Ù„Ø­Ù‚Ù„': 'Ø¹Ø¯Ø¯ Ø§Ù„Ø¯Ø¹ÙˆØ§Øª', 'Ø§Ù„ÙˆØµÙ ': 'Ø¹Ø¯Ø¯ Ø§Ù„Ø¯Ø¹ÙˆØ§Øª Ø§Ù„Ù…Ø·Ù„ÙˆØ¨Ø© Ù„Ù‡Ø°Ø§ Ø§Ù„Ø¶ÙŠÙ ', 'Ù…Ø·Ù„ÙˆØ¨': 'Ù†Ø¹Ù…', 'Ù…Ø«Ø§Ù„': '3' },
  { 'Ø§Ù„Ø­Ù‚Ù„': 'Ù†ÙˆØ¹ Ø§Ù„ØªØ°ÙƒØ±Ø©', 'Ø§Ù„ÙˆØµÙ ': 'vip Ø£Ùˆ normal', 'Ù…Ø·Ù„ÙˆØ¨': 'Ù„Ø§', 'Ù…Ø«Ø§Ù„': 'vip' },
]

export function EventInvitationsTab({ event, stats }: Props) {
  const [vipCount, setVipCount] = useState(0)
  const [normalCount, setNormalCount] = useState(0)
  const [guestPrefix, setGuestPrefix] = useState('ضيف')
  const sourceStorageKey = `event-invitations-source:${event.id}`
  const designModeStorageKey = `event-invitations-design-mode:${event.id}`
  const [generationSource, setGenerationSource] = useState<'manual' | 'excel' | 'design'>(() => {
    if (typeof window === 'undefined') return 'manual'
    // If returning from design editor with templateId or source=design, auto-select design tab
    const params = new URLSearchParams(window.location.search)
    if (params.get('templateId') || params.get('source') === 'design') return 'design'
    const saved = window.localStorage.getItem(sourceStorageKey)
    return saved === 'manual' || saved === 'excel' || saved === 'design' ? saved : 'manual'
  })

  // excel tab import state
  const [excelImportedGuests, setExcelImportedGuests] = useState<GuestImportRow[]>([])
  const [excelImportFileName, setExcelImportFileName] = useState('')
  const [excelImportErrors, setExcelImportErrors] = useState<string[]>([])

  // custom design tab import state
  const [designImportedGuests, setDesignImportedGuests] = useState<GuestImportRow[]>([])
  const [designImportFileName, setDesignImportFileName] = useState('')
  const [designImportErrors, setDesignImportErrors] = useState<string[]>([])

  const [showSettings, setShowSettings] = useState(false)
  const [layout, setLayout] = useState<LayoutConfig>({ ...DEFAULT_LAYOUT })
  const [singleGuestName, setSingleGuestName] = useState('')
  const [singleGuestCount, setSingleGuestCount] = useState(1)
  const [singleGuestClass, setSingleGuestClass] = useState<'vip' | 'normal'>('normal')
  const [showSingleGuestModal, setShowSingleGuestModal] = useState(false)
  const { mutate: generate, isPending, data, isError, error } = useGenerateInvitations()
  const [localError, setLocalError] = useState<string | null>(null)
  const [designCount, setDesignCount] = useState(1)
  const [designTicketClass, setDesignTicketClass] = useState<'vip' | 'normal'>('normal')
  const [designInputMode, setDesignInputMode] = useState<'count' | 'excel'>(() => {
    if (typeof window === 'undefined') return 'count'
    const saved = window.localStorage.getItem(designModeStorageKey)
    return saved === 'count' || saved === 'excel' ? saved : 'count'
  })
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const initialTemplateId = searchParams.get('templateId') || ''
  const initialTicketClass = searchParams.get('ticketClass')
  const [designTemplateId, setDesignTemplateId] = useState(initialTemplateId)
  const [designTemplateName, setDesignTemplateName] = useState('')
  const { data: templates = [], refetch: refetchTemplates } = useQuery({
    queryKey: ['event-templates', event.id],
    queryFn: () => templatesApi.list(event.id),
  })

  // State for previewing templates in custom design mode
  const [selectedTemplateForPreview, setSelectedTemplateForPreview] = useState<any>(null)
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
    setSelectedTemplateForPreview(template)
    await previewMutation.mutateAsync(template.id)
    setShowPreviewModal(true)
  }

  const handleDeleteTemplate = (template: any) => {
    if (window.confirm(`هل أنت متأكد من حذف القالب "${template.name}"؟`)) {
      setSelectedTemplateForPreview(template)
      deleteMutation.mutate(template.id)
    }
  }

  const handleDownloadPreview = async () => {
    if (!selectedTemplateForPreview) return
    await previewMutation.mutateAsync(selectedTemplateForPreview.id)
  }

  // ── Track which templates have dynamic text elements using useQueries ──
  const designedTemplates = useMemo(() => {
    return templates.filter((t) => t.template_type === 'designed')
  }, [templates])

  const elementsQueries = useQueries({
    queries: designedTemplates.map((tpl) => ({
      queryKey: ['template-elements', tpl.id],
      queryFn: () => templatesApi.getElements(tpl.id),
      staleTime: 1000 * 60 * 5, // cache for 5 minutes
    })),
  })

  const designedTemplatesWithMetadata = useMemo(() => {
    return designedTemplates.map((tpl, index) => {
      const query = elementsQueries[index]
      const elements = query?.data || []
      const isLoading = query ? query.isLoading : true
      const isError = query ? query.isError : false
      
      const dynamicElements = elements.filter(
        (el) => el.element_type === 'dynamic_text' || el.element_type === 'guest_name',
      )
      
      return {
        template: tpl,
        isLoading,
        isError,
        hasDynamic: dynamicElements.length > 0,
        dynamicCount: dynamicElements.length,
      }
    })
  }, [designedTemplates, elementsQueries])

  const isTemplatesLoading = useMemo(() => {
    return elementsQueries.some((q) => q.isLoading)
  }, [elementsQueries])

  useEffect(() => {
    if (initialTemplateId && templates.length > 0) {
      const tpl = templates.find((t) => t.id === initialTemplateId)
      if (tpl && !designTemplateName) {
        setDesignTemplateName(tpl.name)
        if (tpl.ticket_class === 'vip' || tpl.ticket_class === 'normal') {
          setDesignTicketClass(tpl.ticket_class)
        } else if (initialTicketClass === 'vip' || initialTicketClass === 'normal') {
          setDesignTicketClass(initialTicketClass)
        }
        setDesignStatus(`تم تحديد القالب: ${tpl.name}`)
      }
    }
  }, [initialTemplateId, initialTicketClass, templates, designTemplateName])
  const [designStatus, setDesignStatus] = useState<string | null>(null)
  const [designBatchId, setDesignBatchId] = useState('')
  // Generation history moved to the barcodes tab (last tab)
  const remainingVip = Math.max(0, event.vip_quota - (stats?.vip_count || 0))
  const remainingNormal = Math.max(0, event.normal_quota - (stats?.normal_count || 0))

  // Smart filtering: ticket class + input mode
  const matchingDesignedTemplates = useMemo(() => {
    return designedTemplatesWithMetadata.filter((item) => {
      const tpl = item.template
      if (tpl.ticket_class !== designTicketClass) return false

      if (designInputMode === 'excel') {
        // Excel mode: only templates WITH dynamic fields (don't show during loading to prevent flicker)
        if (item.isLoading) return false
        return item.hasDynamic
      } else {
        // Count mode: show all (loading or loaded)
        return true
      }
    })
  }, [designedTemplatesWithMetadata, designTicketClass, designInputMode])

  const designedLayout: BatchLayoutConfig = {
    page_size: 'A4',
    orientation: 'portrait',
    rows: 1,
    cols: 1,
    margin_top_mm: 0,
    margin_bottom_mm: 0,
    margin_left_mm: 0,
    margin_right_mm: 0,
    gap_x_mm: 0,
    gap_y_mm: 0,
    barcode_size_px: 420,
    barcode_size_mode: 'contain',
    show_code_text: false,
    show_guest_name: false,
    caption_field: 'none',
    dpi: 300,
    card_per_page: true,
    barcode_render: 'png',
    cell_padding_mm: 0,
  }

  const {
    data: designBatch,
  } = useQuery({
    queryKey: ['design-batch', event.id, designBatchId],
    queryFn: () => batchesApi.get(designBatchId),
    enabled: !!designBatchId,
    refetchInterval: designBatchId ? 3000 : false,
  })

  useEffect(() => {
    if (!designBatchId || !designBatch) return
    if (designBatch.status === 'ready' && designBatch.result_pdf_url) {
      setDesignStatus('اكتمل التوليد ويمكنك تنزيل الملفات الآن')
    } else if (designBatch.status === 'failed') {
      setDesignStatus('فشلت عملية التوليد')
    } else {
      setDesignStatus(`حالة الدفعة: ${designBatch.status} · %${designBatch.progress}`)
    }
  }, [designBatchId, designBatch])

  useEffect(() => {
    if (typeof window === 'undefined') return
    window.localStorage.setItem(sourceStorageKey, generationSource)
  }, [generationSource, sourceStorageKey])

  useEffect(() => {
    if (typeof window === 'undefined') return
    window.localStorage.setItem(designModeStorageKey, designInputMode)
  }, [designInputMode, designModeStorageKey])

  useEffect(() => {
    if (!designTemplateId) return
    const selected = templates.find((tpl) => tpl.id === designTemplateId)
    if (selected && selected.ticket_class !== designTicketClass) {
      setDesignTemplateId('')
      setDesignTemplateName('')
    }
  }, [designTicketClass, designTemplateId, templates])

  // Clear selected template when switching mode if it doesn't fit
  useEffect(() => {
    if (!designTemplateId) return
    const match = designedTemplatesWithMetadata.find((m) => m.template.id === designTemplateId)
    if (!match || match.isLoading) return

    if (designInputMode === 'excel' && !match.hasDynamic) {
      // Switching to Excel but selected template has no dynamic fields
      setDesignTemplateId('')
      setDesignTemplateName('')
    }
  }, [designInputMode, designTemplateId, designedTemplatesWithMetadata])

  const updateLayout = (patch: Partial<LayoutConfig>) =>
    setLayout((prev) => ({ ...prev, ...patch }))

  const downloadExcelTemplate = () => {
    const workbook = XLSX.utils.book_new()
    const worksheet = XLSX.utils.json_to_sheet(TEMPLATE_ROWS)
    const guideWorksheet = XLSX.utils.json_to_sheet(TEMPLATE_GUIDE_ROWS)
    XLSX.utils.book_append_sheet(workbook, worksheet, 'Guests')
    XLSX.utils.book_append_sheet(workbook, guideWorksheet, 'Guide')
    XLSX.writeFile(workbook, `guest-import-template-${event.id.slice(0, 8)}.xlsx`)
  }

  const clearImportedGuests = (target: 'excel' | 'design') => {
    if (target === 'excel') {
      setExcelImportedGuests([])
      setExcelImportFileName('')
      setExcelImportErrors([])
    } else {
      setDesignImportedGuests([])
      setDesignImportFileName('')
      setDesignImportErrors([])
    }
  }

  const addSingleGuest = () => {
    const guestName = singleGuestName.trim()
    if (!guestName) {
      setLocalError('اكتب اسم الشخص أولاً')
      return
    }
    if (!Number.isFinite(singleGuestCount) || singleGuestCount < 1) {
      setLocalError('عدد الأشخاص يجب أن يكون 1 على الأقل')
      return
    }

    setExcelImportedGuests((prev) => [
      ...prev,
      {
        guest_name: guestName,
        invitation_count: Math.floor(singleGuestCount),
        ticket_class: singleGuestClass,
      },
    ])
    setExcelImportErrors([])
    setExcelImportFileName((prev) => prev || 'دعوات مضافة يدويًا')
    setGenerationSource('excel')
    setSingleGuestName('')
    setSingleGuestCount(1)
    setSingleGuestClass('normal')
    setLocalError(null)
    setShowSingleGuestModal(false)
  }

  const parseTicketClass = (value: unknown): 'vip' | 'normal' => {
    const normalized = String(value ?? '').trim().toLowerCase()
    if (['vip', 'v', 'كبار الشخصيات'].includes(normalized)) return 'vip'
    return 'normal'
  }

  const handleGuestFileSelected = async (file: File | null, target: 'excel' | 'design') => {
    if (!file) return
    setLocalError(null)
    if (target === 'excel') {
      setExcelImportErrors([])
    } else {
      setDesignImportErrors([])
    }

    try {
      const buffer = await file.arrayBuffer()
      const workbook = XLSX.read(buffer, { type: 'array' })
      const firstSheet = workbook.Sheets[workbook.SheetNames[0]]
      const rows = XLSX.utils.sheet_to_json<Record<string, unknown>>(firstSheet, { defval: '' })

      const parsedRows: GuestImportRow[] = []
      const errors: string[] = []

      rows.forEach((row, index) => {
        const guestName = String(row['اسم الضيف'] ?? row['guest_name'] ?? row['name'] ?? '').trim()
        const invitationCountRaw = row['عدد الأشخاص'] ?? row['عدد الدعوات'] ?? row['invitation_count'] ?? row['count'] ?? 1
        const invitationCount = Number(invitationCountRaw)
        const ticketClass = parseTicketClass(row['نوع التذكرة'] ?? row['ticket_class'] ?? row['class'])

        // Collect all other columns as custom fields for dynamic rendering
        const custom_fields: Record<string, string> = {}
        for (const [key, value] of Object.entries(row)) {
          if (!['اسم الضيف', 'guest_name', 'name', 'عدد الأشخاص', 'عدد الدعوات', 'invitation_count', 'count', 'نوع التذكرة', 'ticket_class', 'class'].includes(key)) {
            if (value !== undefined && value !== null && value !== '') {
              custom_fields[key] = String(value)
            }
          }
        }

        if (!guestName) {
          errors.push(`السطر ${index + 2}: اسم الضيف مفقود`)
          return
        }
        if (!Number.isFinite(invitationCount) || invitationCount < 1 || invitationCount > 100) {
          errors.push(`السطر ${index + 2}: عدد الدعوات يجب أن يكون بين 1 و100`)
          return
        }

        parsedRows.push({
          guest_name: guestName,
          invitation_count: Math.floor(invitationCount),
          ticket_class: ticketClass,
          custom_fields,
        })
      })

      if (!parsedRows.length) {
        if (target === 'excel') {
          setExcelImportErrors(errors.length ? errors : ['لم يتم العثور على صفوف صالحة داخل الملف'])
          setExcelImportedGuests([])
          setExcelImportFileName(file.name)
        } else {
          setDesignImportErrors(errors.length ? errors : ['لم يتم العثور على صفوف صالحة داخل الملف'])
          setDesignImportedGuests([])
          setDesignImportFileName(file.name)
        }
        return
      }

      if (target === 'excel') {
        setExcelImportedGuests(parsedRows)
        setExcelImportFileName(file.name)
        setExcelImportErrors(errors)
        if (generationSource !== 'design') {
          setGenerationSource('excel')
        }
      } else {
        setDesignImportedGuests(parsedRows)
        setDesignImportFileName(file.name)
        setDesignImportErrors(errors)
      }
    } catch {
      if (target === 'excel') {
        setExcelImportedGuests([])
        setExcelImportFileName(file.name)
        setExcelImportErrors(['تعذر قراءة الملف. استخدم ملف Excel بصيغة .xlsx أو .xls'])
      } else {
        setDesignImportedGuests([])
        setDesignImportFileName(file.name)
        setDesignImportErrors(['تعذر قراءة الملف. استخدم ملف Excel بصيغة .xlsx أو .xls'])
      }
    }
  }

  const handleGenerate = () => {
    if (generationSource === 'excel' && excelImportedGuests.length === 0) return
    if (generationSource === 'manual' && vipCount === 0 && normalCount === 0) return
    setLocalError(null)

    const invitations: Array<{ guest_name: string; ticket_class: 'vip' | 'normal'; guest_count?: number }> = []
    if (generationSource === 'excel') {
      excelImportedGuests.forEach((guest) => {
        invitations.push({
          guest_name: guest.guest_name,
          ticket_class: guest.ticket_class,
          guest_count: guest.invitation_count,
        })
      })
    } else {
      for (let i = 0; i < vipCount; i++)
        invitations.push({ guest_name: `${guestPrefix} VIP ${i + 1}`, ticket_class: 'vip' as const })
      for (let i = 0; i < normalCount; i++)
        invitations.push({ guest_name: `${guestPrefix} ${i + 1}`, ticket_class: 'normal' as const })
    }

    generate(
      {
        event_id: event.id,
        invitations,
        generate_pdf: true,
        generate_zip: true,
        upload_individual_barcodes: false,
        layout_config: {
          ...layout,
          show_code_text: false,
          show_guest_name: false,
        },
      },
      { onError: (err: any) => setLocalError(err.response?.data?.detail || err.message || 'حدث خطأ غير متوقع') },
    )
  }

  const handleGenerateDesigned = async () => {
    if (!designTemplateId) {
      setLocalError('احفظ القالب أولاً من محرر التصميم')
      return
    }
    if (designInputMode === 'count' && designCount < 1) {
      setLocalError('عدد الدعوات يجب أن يكون 1 على الأقل')
      return
    }
    if (designInputMode === 'excel' && designImportedGuests.length === 0) {
      setLocalError('ارفع ملف Excel أولاً')
      return
    }

    setLocalError(null)
    setDesignStatus(null)

    try {
      const invitationIds: string[] = []

      if (designInputMode === 'count') {
        const created = await invitationsAPI.quickCreate({
          event_id: event.id,
          template_id: designTemplateId,
          ticket_class: designTicketClass,
          count: designCount,
        })
        invitationIds.push(...created.invitations.map((item: any) => String(item.id)))
      } else {
        const guestsForClass = designImportedGuests.filter((guest) => guest.ticket_class === designTicketClass)
        if (!guestsForClass.length) {
          throw new Error(`لا توجد دعوات ${designTicketClass === 'vip' ? 'VIP' : 'عادية'} في ملف Excel`)
        }
        for (const guest of guestsForClass) {
          const created = await invitationsAPI.create({
            event_id: event.id,
            template_id: designTemplateId,
            ticket_class: guest.ticket_class,
            guest_name: guest.guest_name,
            guest_count: guest.invitation_count,
            metadata: { 
              imported_from: designImportFileName || 'Excel',
              custom_fields: guest.custom_fields || {}
            },
          })
          invitationIds.push(created.id)
        }
      }

      if (!invitationIds.length) {
        throw new Error('لم يتم إنشاء أي دعوات')
      }

      const batch = await batchesApi.create({
        event_id: event.id,
        template_id: designTemplateId,
        mode: 'designed',
        ticket_class: designTicketClass,
        invitation_ids: invitationIds,
        layout: designedLayout,
        output_formats: ['pdf', 'zip'],
        barcode_format: 'qr',
        metadata: {
          template_name: designTemplateName || undefined,
          source: designInputMode,
        },
      })

      setDesignBatchId(batch.id)
      await batchesApi.start(batch.id)
      setDesignStatus(`تم بدء التوليد المصمم (${invitationIds.length} دعوة)`) 
    } catch (err: any) {
      setLocalError(err.response?.data?.detail || err.message || 'تعذر بدء التوليد المصمم')
    }
  }

  const importedVipCount = excelImportedGuests.reduce((sum, guest) => sum + (guest.ticket_class === 'vip' ? guest.invitation_count : 0), 0)
  const importedNormalCount = excelImportedGuests.reduce((sum, guest) => sum + (guest.ticket_class === 'normal' ? guest.invitation_count : 0), 0)
  const plannedVipCount = generationSource === 'excel' ? importedVipCount : vipCount
  const plannedNormalCount = generationSource === 'excel' ? importedNormalCount : normalCount
  const totalImportedGuests = excelImportedGuests.length
  const isFormValid =
    (plannedVipCount > 0 || plannedNormalCount > 0) &&
    plannedVipCount <= remainingVip &&
    plannedNormalCount <= remainingNormal
  const barcodePerPage = layout.rows * layout.cols
  const totalInvitations = plannedVipCount + plannedNormalCount
  const estimatedPages = totalInvitations > 0 ? Math.ceil(totalInvitations / barcodePerPage) : 0

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* ═══ GENERATION CARD ═══ */}
      <section className="inv-card">
        <div className="inv-card__header">
          <div className="inv-card__icon inv-card__icon--gold"><Printer size={20} /></div>
          <div>
            <h3 className="inv-card__title">توليد الدعوات للطباعة</h3>
            <p className="inv-card__desc">توليد ملفات PDF و ZIP للدعوات الجاهزة للطباعة</p>
          </div>
        </div>

        <div className="inv-card__body">
          <div className="inv-source-switch">
            <button
              type="button"
              className={`inv-source-switch__btn ${generationSource === 'manual' ? 'inv-source-switch__btn--active' : ''}`}
              onClick={() => setGenerationSource('manual')}
            >
              <Users size={15} /> إدخال يدوي
            </button>
            <button
              type="button"
              className={`inv-source-switch__btn ${generationSource === 'excel' ? 'inv-source-switch__btn--active' : ''}`}
              onClick={() => setGenerationSource('excel')}
            >
              <FileSpreadsheet size={15} /> من ملف Excel
            </button>
            <button
              type="button"
              className={`inv-source-switch__btn ${generationSource === 'design' ? 'inv-source-switch__btn--active' : ''}`}
              onClick={() => setGenerationSource('design')}
            >
              <QrCode size={15} /> تصميم مخصص
            </button>
            <button
              type="button"
              className="inv-source-switch__btn"
              onClick={() => {}}
              title="نظام احترافي لاختيار النوع والقالب والملف"
            >
              <Sparkles size={15} /> نموذج احترافي
            </button>
          </div>

          {generationSource === 'manual' && <>
          {/* VIP + Normal counters */}
          <div className="inv-grid-2">
            {/* VIP */}
            <div className="inv-tier-box inv-tier-box--vip">
              <div className="inv-tier-box__glow" />
              <div className="inv-tier-box__head">
                <span className="inv-tier-box__label inv-tier-box__label--vip">
                  <Sparkles size={15} /> تذاكر VIP
                </span>
                <span className="inv-tier-box__badge inv-tier-box__badge--vip">المتبقي: {remainingVip}</span>
              </div>
              <label className="inv-label">عدد الدعوات المطلوب توليدها</label>
              <input
                type="number" min={0} max={remainingVip} value={vipCount || ''}
                onChange={(e) => setVipCount(parseInt(e.target.value) || 0)}
                className="inv-input" placeholder="0" disabled={isPending}
              />
            </div>

            {/* Normal */}
            <div className="inv-tier-box inv-tier-box--normal">
              <div className="inv-tier-box__head">
                <span className="inv-tier-box__label">
                  <Users size={15} /> تذاكر الدخول العادي
                </span>
                <span className="inv-tier-box__badge">المتبقي: {remainingNormal}</span>
              </div>
              <label className="inv-label">عدد الدعوات المطلوب توليدها</label>
              <input
                type="number" min={0} max={remainingNormal} value={normalCount || ''}
                onChange={(e) => setNormalCount(parseInt(e.target.value) || 0)}
                className="inv-input" placeholder="0" disabled={isPending}
              />
            </div>
          </div>

          {/* Guest prefix */}
          <div style={{ maxWidth: 400, marginBottom: 8 }}>
            <label className="inv-label">بادئة اسم الضيف (مثال: ضيف 1، ضيف 2)</label>
            <input type="text" value={guestPrefix} onChange={(e) => setGuestPrefix(e.target.value)}
              className="inv-input" placeholder="ضيف" disabled={isPending} />
          </div>

          {/* ═══ PDF SETTINGS PANEL ═══ */}
          </>}

          {generationSource === 'excel' && (
            <div className="inv-import-card">
              <div className="inv-import-card__header">
                <div>
                  <strong>رفع ملف الضيوف</strong>
                  <span>ارفع ملف Excel يحتوي على اسم الضيف، عدد الأشخاص، ونوع التذكرة</span>
                </div>
                <div className="inv-import-card__header-actions">
                  <button type="button" className="inv-dl-btn inv-dl-btn--zip" onClick={downloadExcelTemplate}>
                    <Download size={15} /> تنزيل النموذج
                  </button>
                  <button type="button" className="inv-quick-add-btn" onClick={() => setShowSingleGuestModal(true)}>
                    <Plus size={15} /> إضافة دعوة واحدة
                  </button>
                </div>
              </div>

              <div className="inv-import-card__actions">
                <label className="inv-upload-btn">
                  <Upload size={15} /> اختيار ملف Excel
                  <input
                    type="file"
                    accept=".xlsx,.xls"
                    onClick={(e) => {
                      e.currentTarget.value = ''
                    }}
                    onChange={(e) => handleGuestFileSelected(e.target.files?.[0] ?? null, 'excel')}
                    hidden
                  />
                </label>
                {excelImportFileName && (
                  <div className="inv-upload-file">
                    <FileSpreadsheet size={15} />
                    <span>{excelImportFileName}</span>
                    <button type="button" className="inv-upload-file__clear" onClick={() => clearImportedGuests('excel')}>
                      <X size={14} />
                    </button>
                  </div>
                )}
              </div>

              {!!excelImportErrors.length && (
                <div className="inv-import-errors">
                  {excelImportErrors.slice(0, 5).map((msg) => (
                    <div key={msg} className="inv-import-errors__item">{msg}</div>
                  ))}
                </div>
              )}

              {!!excelImportedGuests.length && (
                <>
                  <div className="inv-import-stats">
                    <div><strong>{totalImportedGuests}</strong><span>سجل/ضيف</span></div>
                    <div><strong>{plannedVipCount}</strong><span>عدد أشخاص VIP</span></div>
                    <div><strong>{plannedNormalCount}</strong><span>عدد الأشخاص العاديين</span></div>
                    <div><strong>{totalInvitations}</strong><span>إجمالي الأشخاص</span></div>
                  </div>
                  <div className="inv-import-preview">
                    {excelImportedGuests.slice(0, 5).map((guest, index) => (
                      <div key={`${guest.guest_name}-${index}`} className="inv-import-preview__row">
                        <strong>{guest.guest_name}</strong>
                        <span>
                          دعوة واحدة · {guest.ticket_class === 'vip' ? 'VIP' : 'عادي'} · {guest.invitation_count} شخص
                        </span>
                      </div>
                    ))}
                    {excelImportedGuests.length > 5 && (
                      <div className="inv-import-preview__more">+{excelImportedGuests.length - 5} صفوف إضافية</div>
                    )}
                  </div>
                </>
              )}
            </div>
          )}

          {generationSource === 'design' && (
            <div className="inv-import-card inv-design-card">
              {/* Header */}
              <div className="inv-import-card__header">
                <div>
                  <strong>تصميم مخصص للدعوات</strong>
                  <span>اختر نوع الدعوة والقالب، ثم ولّد ملفات PDF/ZIP جاهزة للطباعة.</span>
                </div>
              </div>

              {/* ═══ Inner tabs (data mode) ═══ */}
              <div className="inv-design-inner-tabs">
                <button
                  type="button"
                  className={`inv-design-inner-tab ${designInputMode === 'count' ? 'inv-design-inner-tab--active' : ''}`}
                  onClick={() => setDesignInputMode('count')}
                >
                  <QrCode size={14} /> باركودات فقط
                </button>
                <button
                  type="button"
                  className={`inv-design-inner-tab ${designInputMode === 'excel' ? 'inv-design-inner-tab--active' : ''}`}
                  onClick={() => setDesignInputMode('excel')}
                >
                  <FileSpreadsheet size={14} /> من ملف Excel
                </button>
              </div>

              {/* ═══ Type + Template + Data — all below tabs ═══ */}
              <div className="inv-design-body">

                {/* Type Selection */}
                <div className="inv-design-section">
                  <label className="inv-design-section__label">نوع الدعوات</label>
                  <div className="inv-design-type-cards">
                    <button
                      type="button"
                      className={`inv-design-type-card ${designTicketClass === 'vip' ? 'inv-design-type-card--active inv-design-type-card--vip' : ''}`}
                      onClick={() => setDesignTicketClass('vip')}
                    >
                      <div className="inv-design-type-card__icon inv-design-type-card__icon--vip">
                        <Sparkles size={22} />
                      </div>
                      <div className="inv-design-type-card__info">
                        <strong>VIP</strong>
                        <span>دعوات فاخرة</span>
                      </div>
                      {designTicketClass === 'vip' && <CheckCircle2 size={18} className="inv-design-type-card__check" />}
                    </button>
                    <button
                      type="button"
                      className={`inv-design-type-card ${designTicketClass === 'normal' ? 'inv-design-type-card--active' : ''}`}
                      onClick={() => setDesignTicketClass('normal')}
                    >
                      <div className="inv-design-type-card__icon">
                        <Users size={22} />
                      </div>
                      <div className="inv-design-type-card__info">
                        <strong>عادي</strong>
                        <span>دعوات عادية</span>
                      </div>
                      {designTicketClass === 'normal' && <CheckCircle2 size={18} className="inv-design-type-card__check" />}
                    </button>
                  </div>
                </div>

                {/* Template Selection */}
                <div className="inv-design-section">
                  <label className="inv-design-section__label">القالب ({designTicketClass === 'vip' ? 'VIP' : 'عادي'})</label>
                  {isTemplatesLoading ? (
                    <div className="inv-design-templates-grid">
                      {[1, 2, 3].map((n) => (
                        <div key={n} className="inv-design-template-skeleton">
                          <div className="inv-design-template-skeleton__thumb" />
                          <div className="inv-design-template-skeleton__name" />
                        </div>
                      ))}
                    </div>
                  ) : matchingDesignedTemplates.length === 0 ? (
                    <div className="inv-design-empty-templates">
                      {designInputMode === 'excel' ? <Database size={28} style={{ opacity: 0.3 }} /> : <QrCode size={28} style={{ opacity: 0.3 }} />}
                      <p>
                        {designInputMode === 'excel'
                          ? `لا توجد قوالب ${designTicketClass === 'vip' ? 'VIP' : 'عادية'} تحتوي بيانات ديناميكية`
                          : `لا توجد قوالب ${designTicketClass === 'vip' ? 'VIP' : 'عادية'} بعد`}
                      </p>
                      <span>
                        {designInputMode === 'excel'
                          ? 'أنشئ قالب جديد وأضف عناصر «نص ديناميكي» لربطها بأعمدة Excel'
                          : 'افتح محرر التصميم لإنشاء قالب جديد'}
                      </span>
                    </div>
                  ) : (
                    <div className="inv-design-templates-grid">
                      {matchingDesignedTemplates.map(({ template: tpl, hasDynamic, dynamicCount }) => {
                        return (
                          <div
                            key={tpl.id}
                            className={`inv-design-template-card ${designTemplateId === tpl.id ? 'inv-design-template-card--active' : ''}`}
                            onClick={() => { setDesignTemplateId(tpl.id); setDesignTemplateName(tpl.name) }}
                          >
                            <div className="inv-design-template-card__thumb-container">
                              {tpl.background_url ? (
                                <img src={tpl.background_url} alt={tpl.name} className="inv-design-template-card__thumb" />
                              ) : (
                                <div className="inv-design-template-card__placeholder">
                                  <QrCode size={24} style={{ opacity: 0.3 }} />
                                </div>
                              )}
                              {/* Hover actions overlay */}
                              <div className="inv-design-template-card__actions-overlay">
                                <button
                                  type="button"
                                  className="inv-card-action-btn inv-card-action-btn--edit"
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    navigate(`/events/${event.id}/design?edit=${tpl.id}`)
                                  }}
                                  title="تحرير التصميم"
                                >
                                  <Pencil size={14} />
                                </button>
                                <button
                                  type="button"
                                  className="inv-card-action-btn inv-card-action-btn--preview"
                                  onClick={async (e) => {
                                    e.stopPropagation()
                                    await handlePreview(tpl)
                                  }}
                                  title="معاينة"
                                  disabled={previewMutation.isPending}
                                >
                                  {previewMutation.isPending && selectedTemplateForPreview?.id === tpl.id ? (
                                    <Loader2 size={14} className="spin" />
                                  ) : (
                                    <Eye size={14} />
                                  )}
                                </button>
                                <button
                                  type="button"
                                  className="inv-card-action-btn inv-card-action-btn--delete"
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    handleDeleteTemplate(tpl)
                                  }}
                                  title="حذف"
                                  disabled={deleteMutation.isPending}
                                >
                                  {deleteMutation.isPending && selectedTemplateForPreview?.id === tpl.id ? (
                                    <Loader2 size={14} className="spin" />
                                  ) : (
                                    <Trash2 size={14} />
                                  )}
                                </button>
                              </div>
                            </div>
                            <div className="inv-design-template-card__name">{tpl.name}</div>
                            {/* Type indicator */}
                            <div className={`inv-design-template-card__type ${hasDynamic ? 'inv-design-template-card__type--dynamic' : ''}`}>
                              {hasDynamic ? <><Database size={10} /> {dynamicCount} حقل</> : <><QrCode size={10} /> QR</>}
                            </div>
                            {designTemplateId === tpl.id && (
                              <div className="inv-design-template-card__badge"><CheckCircle2 size={14} /></div>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>

                {/* Data Input */}
                <div className="inv-design-section">
                  {designInputMode === 'count' ? (
                    <>
                      <label className="inv-design-section__label">عدد الدعوات</label>
                      <div className="inv-design-tab-row">
                        <input
                          type="number"
                          min={1}
                          max={10000}
                          value={designCount}
                          onChange={(e) => setDesignCount(parseInt(e.target.value) || 1)}
                          className="inv-input"
                          style={{ width: 160 }}
                          disabled={isPending}
                        />
                        <button type="button" className="inv-design-editor-btn" onClick={() => navigate(`/events/${event.id}/design?mode=count`)}>
                          <Sparkles size={14} /> فتح محرر التصميم
                        </button>
                      </div>
                    </>
                  ) : (
                    <>
                      <label className="inv-design-section__label">ملف بيانات الضيوف</label>
                      <div className="inv-design-tab-row">
                        <label className="inv-upload-btn">
                          <Upload size={15} /> اختيار ملف Excel
                          <input
                            type="file"
                            accept=".xlsx,.xls"
                            onClick={(e) => { e.currentTarget.value = '' }}
                            onChange={(e) => handleGuestFileSelected(e.target.files?.[0] ?? null, 'design')}
                            hidden
                          />
                        </label>
                        {designImportFileName && (
                          <div className="inv-upload-file">
                            <FileSpreadsheet size={15} />
                            <span>{designImportFileName}</span>
                            <button type="button" className="inv-upload-file__clear" onClick={() => clearImportedGuests('design')}>
                              <X size={14} />
                            </button>
                          </div>
                        )}
                        <button type="button" className="inv-design-editor-btn" onClick={() => navigate(`/events/${event.id}/design?mode=excel`)}>
                          <Sparkles size={14} /> فتح محرر التصميم
                        </button>
                      </div>
                    </>
                  )}
                </div>

                {/* File validation errors */}
                {!!designImportErrors.length && (
                  <div className="inv-import-errors">
                    {designImportErrors.slice(0, 5).map((msg) => (
                      <div key={msg} className="inv-import-errors__item">{msg}</div>
                    ))}
                  </div>
                )}

                {/* Import stats & preview */}
                {!!designImportedGuests.length && (
                  <>
                    <div className="inv-import-stats">
                      <div><strong>{designImportedGuests.length}</strong><span>سجل/دعوة</span></div>
                      <div><strong>{designImportedGuests.reduce((sum, guest) => sum + guest.invitation_count, 0)}</strong><span>إجمالي الأشخاص</span></div>
                    </div>
                    <div className="inv-import-preview">
                      {designImportedGuests.slice(0, 5).map((guest, index) => (
                        <div key={`${guest.guest_name}-${index}`} className="inv-import-preview__row">
                          <strong>{guest.guest_name}</strong>
                          <span>{guest.ticket_class === 'vip' ? 'VIP' : 'عادي'} · {guest.invitation_count} شخص</span>
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </div>

              {/* Generate button */}
              <button
                type="button"
                className="inv-generate-btn"
                onClick={handleGenerateDesigned}
                disabled={isPending || !designTemplateId}
                style={{ marginTop: 12 }}
              >
                <Printer size={18} /> {isPending ? 'جاري التوليد...' : `بدء التوليد (${designInputMode === 'count' ? designCount : designImportedGuests.length} دعوة)`}
              </button>

              {designStatus && <div className="inv-toast inv-toast--success"><CheckCircle2 size={16} /> {designStatus}</div>}

              {designBatch && (
                <div className="inv-design-batch-card">
                  <div className="inv-design-batch-card__meta">
                    <strong>حالة الدفعة</strong>
                    <span>{designBatch.status} · {designBatch.progress}% · {designBatch.count_total} دعوة</span>
                  </div>
                  <div className="inv-design-batch-card__actions">
                    {designBatch.result_pdf_url && (
                      <a className="inv-dl-btn inv-dl-btn--zip" href={designBatch.result_pdf_url} target="_blank" rel="noreferrer">
                        <Download size={14} /> PDF
                      </a>
                    )}
                    {designBatch.result_zip_url && (
                      <a className="inv-dl-btn inv-dl-btn--zip" href={designBatch.result_zip_url} target="_blank" rel="noreferrer">
                        <Download size={14} /> ZIP
                      </a>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {showSingleGuestModal && (
            <div className="inv-quick-modal-overlay" role="dialog" aria-modal="true">
              <div className="inv-quick-modal">
                <div className="inv-quick-modal__header">
                  <div>
                    <h3>إضافة دعوة واحدة</h3>
                    <p>أدخل الاسم ونوع التذكرة ثم أضفها إلى قائمة Excel الحالية.</p>
                  </div>
                  <button type="button" className="inv-quick-modal__close" onClick={() => setShowSingleGuestModal(false)}>
                    <X size={16} />
                  </button>
                </div>

                <div className="inv-quick-modal__body">
                  <div>
                    <label className="inv-label">اسم الشخص</label>
                    <input
                      type="text"
                      value={singleGuestName}
                      onChange={(e) => setSingleGuestName(e.target.value)}
                      className="inv-input"
                      placeholder="مثال: أحمد محمد"
                      disabled={isPending}
                    />
                  </div>

                  <div>
                    <label className="inv-label">عدد الأشخاص</label>
                    <input
                      type="number"
                      min={1}
                      max={100}
                      value={singleGuestCount}
                      onChange={(e) => setSingleGuestCount(parseInt(e.target.value) || 1)}
                      className="inv-input"
                      placeholder="1"
                      disabled={isPending}
                    />
                  </div>

                  <div>
                    <label className="inv-label">نوع التذكرة</label>
                    <div className="inv-quick-modal__chips">
                      <button
                        type="button"
                        className={`inv-chip ${singleGuestClass === 'normal' ? 'inv-chip--active' : ''}`}
                        onClick={() => setSingleGuestClass('normal')}
                        disabled={isPending}
                      >
                        عادي
                      </button>
                      <button
                        type="button"
                        className={`inv-chip ${singleGuestClass === 'vip' ? 'inv-chip--active' : ''}`}
                        onClick={() => setSingleGuestClass('vip')}
                        disabled={isPending}
                      >
                        VIP
                      </button>
                    </div>
                  </div>

                  {localError && <div className="inv-toast inv-toast--error"><AlertCircle size={16} /> {localError}</div>}
                </div>

                <div className="inv-quick-modal__actions">
                  <button type="button" className="inv-modal__close" onClick={() => setShowSingleGuestModal(false)}>
                    إلغاء
                  </button>
                  <button type="button" className="inv-upload-btn" onClick={addSingleGuest} disabled={isPending}>
                    <Plus size={15} /> إضافة
                  </button>
                </div>
              </div>
            </div>
          )}


          {generationSource !== 'design' && (
          <div className="inv-settings-panel">
            <button className="inv-settings-toggle" onClick={() => setShowSettings(!showSettings)}>
              <div className="inv-settings-toggle__right">
                <Settings2 size={16} style={{ color: 'var(--color-primary)' }} />
                <span>إعدادات PDF والشبكة</span>
                {totalInvitations > 0 && (
                  <span className="inv-settings-tag">{layout.rows}×{layout.cols} · {estimatedPages} صفحة</span>
                )}
              </div>
              {showSettings ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>

            {showSettings && (
              <div className="inv-settings-body">
                {/* Grid Presets */}
                <div>
                  <label className="inv-label" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <Grid3X3 size={14} style={{ opacity: 0.7 }} /> حجم الشبكة (صفوف × أعمدة)
                  </label>
                  <div className="inv-chip-group">
                    {GRID_PRESETS.map((p) => (
                      <button key={p.label}
                        className={`inv-chip ${layout.rows === p.rows && layout.cols === p.cols ? 'inv-chip--active' : ''}`}
                        onClick={() => updateLayout({ rows: p.rows, cols: p.cols })}
                      >{p.label}</button>
                    ))}
                  </div>
                  <div className="inv-custom-grid">
                    <div className="inv-custom-grid__field">
                      <span>صفوف</span>
                      <input type="number" min={1} max={20} value={layout.rows}
                        onChange={(e) => updateLayout({ rows: Math.max(1, Math.min(20, parseInt(e.target.value) || 1)) })}
                        className="inv-input inv-input--sm" />
                    </div>
                    <span className="inv-custom-grid__sep">×</span>
                    <div className="inv-custom-grid__field">
                      <span>أعمدة</span>
                      <input type="number" min={1} max={20} value={layout.cols}
                        onChange={(e) => updateLayout({ cols: Math.max(1, Math.min(20, parseInt(e.target.value) || 1)) })}
                        className="inv-input inv-input--sm" />
                    </div>
                    <span className="inv-custom-grid__info">= {barcodePerPage} دعوات/صفحة</span>
                  </div>
                </div>

                {/* Barcode Size */}
                <div>
                  <label className="inv-label">حجم صورة رمز QR (بكسل)</label>
                  <div className="inv-chip-group">
                    {BARCODE_SIZES.map((s) => (
                      <button key={s.label}
                        className={`inv-chip ${layout.barcode_size_px === s.value ? 'inv-chip--active' : ''}`}
                        onClick={() => updateLayout({ barcode_size_px: s.value })}
                      >{s.label}</button>
                    ))}
                  </div>
                </div>

                {/* Page size & orientation */}
                <div className="inv-grid-2">
                  <div>
                    <label className="inv-label">حجم الصفحة</label>
                    <select value={layout.page_size} onChange={(e) => updateLayout({ page_size: e.target.value as 'A4' | 'Letter' })} className="inv-input">
                      <option value="A4">A4</option>
                      <option value="Letter">Letter</option>
                    </select>
                  </div>
                  <div>
                    <label className="inv-label">الاتجاه</label>
                    <select value={layout.orientation} onChange={(e) => updateLayout({ orientation: e.target.value as 'portrait' | 'landscape' })} className="inv-input">
                      <option value="portrait">عمودي (Portrait)</option>
                      <option value="landscape">أفقي (Landscape)</option>
                    </select>
                  </div>
                </div>

                {/* Toggles */}
                <div className="inv-toggle-row">
                  <button className={`inv-toggle-btn ${layout.show_guest_name ? 'inv-toggle-btn--on' : ''}`}
                    onClick={() => updateLayout({ show_guest_name: !layout.show_guest_name })}>
                    {layout.show_guest_name ? <Eye size={14} /> : <EyeOff size={14} />} اسم الضيف
                  </button>
                  <button className={`inv-toggle-btn ${layout.show_code_text ? 'inv-toggle-btn--on' : ''}`}
                    onClick={() => updateLayout({ show_code_text: !layout.show_code_text })}>
                    {layout.show_code_text ? <Eye size={14} /> : <EyeOff size={14} />} رمز الدعوة
                  </button>
                </div>

                {/* Summary */}
                {totalInvitations > 0 && (
                  <div className="inv-summary-bar">
                    <span><strong>{totalInvitations}</strong> دعوة</span>
                    <span className="inv-summary-bar__dot" />
                    <span><strong>{layout.rows}×{layout.cols}</strong> شبكة</span>
                    <span className="inv-summary-bar__dot" />
                    <span><strong>{estimatedPages}</strong> صفحة</span>
                    <span className="inv-summary-bar__dot" />
                    <span>رمز QR: <strong>{layout.barcode_size_px ? `${layout.barcode_size_px}px` : 'تلقائي'}</strong></span>
                  </div>
                )}
              </div>
            )}
          </div>
          )}

          {/* Generate Button */}
          {generationSource !== 'design' && (
          <button onClick={handleGenerate} disabled={!isFormValid || isPending} className="inv-generate-btn">
              {isPending ? (
              <><Loader2 size={18} className="animate-spin" /> جاري توليد الدعوات...</>
            ) : (
              <><Printer size={18} /> بدء التوليد ({totalInvitations} دعوة)</>
            )}
          </button>
          )}

          {/* Error */}
          {(localError || (isError && error)) && (
            <div className="inv-toast inv-toast--error">
              <AlertCircle size={16} /> {localError || (error as any)?.message}
            </div>
          )}
        </div>

        {/* Success Result */}
        {data?.success && (
          <div className="inv-result">
            <div className="inv-result__info">
              <CheckCircle2 size={20} />
              <div>
                <strong>تم توليد الدعوات بنجاح!</strong>
                <span>{data.total_invitations} دعوة في {data.generation_time_ms}ms</span>
              </div>
            </div>
            <div className="inv-result__actions">
              {data.pdf_url && (
                <a href={data.pdf_url} target="_blank" rel="noopener noreferrer" className="inv-dl-btn inv-dl-btn--pdf">
                  <Download size={16} /> PDF ({data.pdf_size_mb?.toFixed(2)} MB)
                </a>
              )}
              {data.zip_url && (
                <a href={data.zip_url} target="_blank" rel="noopener noreferrer" className="inv-dl-btn inv-dl-btn--zip">
                  <Download size={16} /> ZIP ({data.zip_size_mb?.toFixed(2)} MB)
                </a>
              )}
            </div>
          </div>
        )}
      </section>

      {/* Preview Modal */}
      {showPreviewModal && (
        <div className="preview-modal-overlay" onClick={() => setShowPreviewModal(false)}>
          <div className="preview-modal" onClick={(e) => e.stopPropagation()}>
            <div className="preview-modal-header">
              <h2>معاينة القالب - {selectedTemplateForPreview?.name}</h2>
              <button
                type="button"
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
                      onChange={(e) => setPreviewData({ ...previewData, guest_name: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label>عنوان الحفل</label>
                    <input
                      type="text"
                      value={previewData.event_title}
                      onChange={(e) => setPreviewData({ ...previewData, event_title: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label>التاريخ</label>
                    <input
                      type="date"
                      value={previewData.event_date}
                      onChange={(e) => setPreviewData({ ...previewData, event_date: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label>الوقت</label>
                    <input
                      type="time"
                      value={previewData.event_time}
                      onChange={(e) => setPreviewData({ ...previewData, event_time: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label>المكان</label>
                    <input
                      type="text"
                      value={previewData.event_location}
                      onChange={(e) => setPreviewData({ ...previewData, event_location: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label>رقم المقعد</label>
                    <input
                      type="text"
                      value={previewData.seat_number}
                      onChange={(e) => setPreviewData({ ...previewData, seat_number: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label>رقم الطاولة</label>
                    <input
                      type="text"
                      value={previewData.table_number}
                      onChange={(e) => setPreviewData({ ...previewData, table_number: e.target.value })}
                    />
                  </div>

                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => previewMutation.mutate(selectedTemplateForPreview?.id!)}
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
                type="button"
                className="btn btn-secondary"
                onClick={() => setShowPreviewModal(false)}
              >
                إغلاق
              </button>
              <button
                type="button"
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
