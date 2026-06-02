import { useEffect, useState, useMemo } from 'react'
import { useQuery, useQueries, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useSearchParams } from 'react-router-dom'
import * as XLSX from 'xlsx'
import http from '@services/http/client'
import { EventModel, EventStats } from '../types'
import { useGenerateInvitations } from '../hooks/useGenerateInvitations'
import { DEFAULT_LAYOUT, type LayoutConfig, type FastInvitationItem } from '../api/invitationsApi'
import { batchesApi, type BatchLayoutConfig } from '../api/batchesApi'
import { templatesApi } from '../api/templatesApi'
import { 
  getCleanFieldLabel, 
  resolveGuestName, 
  resolveGuestCount, 
  resolveTicketClass,
  formatCellValue
} from '../utils/mappingUtils'

import {
  Printer, Download, Users, Loader2, Sparkles,
  Settings2, Grid3X3, ChevronDown, ChevronUp, Eye, EyeOff,
  CheckCircle2, AlertCircle, Upload, FileSpreadsheet, X, Plus, QrCode, Database,
  Pencil, Trash2, Info,
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

interface DesignExcelColumn {
  name: string
  index: number
  sampleValues: string[]
}

interface DynamicField {
  data_key: string
  label: string
  element_type: string
  required: boolean
}

const BUILTIN_FIELDS: DynamicField[] = [
  { data_key: 'guest.name', label: 'اسم الضيف', element_type: 'guest_name', required: true },
]

const ALIAS_MAP: Record<string, string[]> = {
  'guest.name': ['اسم الضيف', 'guest_name', 'name', 'اسم', 'الاسم', 'guestname', 'الضيف'],
  'event.date': ['تاريخ', 'event_date', 'date', 'التاريخ'],
  'event.time': ['وقت', 'event_time', 'time', 'الوقت'],
  'custom.seat': ['مقعد', 'seat_number', 'seat', 'رقم المقعد'],
  'custom.table': ['طاولة', 'table_number', 'table', 'رقم الطاولة'],
  'custom.gate': ['بوابة', 'gate', 'البوابة'],
  'custom.hall': ['قاعة', 'hall', 'القاعة'],
}

const sanitizeArabicDigits = (val: any): string => {
  return String(val || '').replace(/[٠-٩]/g, (c) => String(c.charCodeAt(0) - 0x0660))
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
  const queryClient = useQueryClient()
  const [vipCount, setVipCount] = useState(0)
  const [normalCount, setNormalCount] = useState(0)
  const [guestPrefix, setGuestPrefix] = useState('ضيف')
  const sourceStorageKey = `event-invitations-source:${event.id}`
  const designModeStorageKey = `event-invitations-design-mode:${event.id}`
  const [generationSource, setGenerationSource] = useState<'quick' | 'design'>(() => {
    if (typeof window === 'undefined') return 'quick'
    // If returning from design editor with templateId or source=design, auto-select design tab
    const params = new URLSearchParams(window.location.search)
    if (params.get('templateId') || params.get('source') === 'design') return 'design'
    const saved = window.localStorage.getItem(sourceStorageKey)
    if (saved === 'manual' || saved === 'excel') return 'quick'
    return saved === 'design' ? 'design' : 'quick'
  })

  const [quickInputMode, setQuickInputMode] = useState<'manual' | 'names' | 'excel'>(() => {
    if (typeof window === 'undefined') return 'manual'
    const saved = window.localStorage.getItem(`event-invitations-quick-mode:${event.id}`)
    const oldSource = window.localStorage.getItem(sourceStorageKey)
    if (oldSource === 'excel') return 'excel'
    return saved === 'manual' || saved === 'names' || saved === 'excel' ? (saved as any) : 'manual'
  })

  // excel tab import state
  const [excelImportedGuests, setExcelImportedGuests] = useState<GuestImportRow[]>([])
  const [excelImportFileName, setExcelImportFileName] = useState('')
  const [excelImportErrors, setExcelImportErrors] = useState<string[]>([])

  // New manual typed guest list states
  const [quickManualGuests, setQuickManualGuests] = useState<GuestImportRow[]>(() => {
    if (typeof window === 'undefined') return []
    const saved = window.localStorage.getItem(`event-invitations-quick-manual:${event.id}`)
    return saved ? JSON.parse(saved) : []
  })
  const [designManualGuests, setDesignManualGuests] = useState<GuestImportRow[]>(() => {
    if (typeof window === 'undefined') return []
    const saved = window.localStorage.getItem(`event-invitations-design-manual:${event.id}`)
    return saved ? JSON.parse(saved) : []
  })

  // States for manual input form
  const [quickFormName, setQuickFormName] = useState('')
  const [quickFormCount, setQuickFormCount] = useState(1)
  const [quickFormClass, setQuickFormClass] = useState<'vip' | 'normal'>('normal')
  const [quickDynamicFields, setQuickDynamicFields] = useState<string[]>(() => {
    if (typeof window === 'undefined') return []
    const saved = window.localStorage.getItem(`event-invitations-quick-dynamic-fields:${event.id}`)
    return saved ? JSON.parse(saved) : []
  })
  const [newQuickFieldName, setNewQuickFieldName] = useState('')
  const [quickFormCustomFields, setQuickFormCustomFields] = useState<Record<string, string>>({})

  const [designFormName, setDesignFormName] = useState('')
  const [designFormCount, setDesignFormCount] = useState(1)
  const [designFormCustomFields, setDesignFormCustomFields] = useState<Record<string, string>>({})

  // custom design tab import state
  const [designImportedGuests, setDesignImportedGuests] = useState<GuestImportRow[]>([])
  const [designImportFileName, setDesignImportFileName] = useState('')
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [designImportErrors, setDesignImportErrors] = useState<string[]>([])
  void designImportErrors // consumed by legacy handlers
  void designImportedGuests
  void designImportFileName

  // ── Inline Excel flow states (for design tab) ──
  const [designExcelFile, setDesignExcelFile] = useState<File | null>(null)
  const [designExcelColumns, setDesignExcelColumns] = useState<DesignExcelColumn[]>([])
  const [designExcelRows, setDesignExcelRows] = useState<Record<string, string>[]>([])
  const [designColumnMapping, setDesignColumnMapping] = useState<Record<string, string>>({})
  const [modalAlert, setModalAlert] = useState<{ title: string; message: string; type: 'success' | 'error' | 'info' } | null>(null)
  const [designMappingErrors, setDesignMappingErrors] = useState<string[]>([])
  const [dynamicFields, setDynamicFields] = useState<DynamicField[]>(BUILTIN_FIELDS)
  const [designTemplateElements, setDesignTemplateElements] = useState<any[]>([])
  const [hoveredFieldKey, setHoveredFieldKey] = useState<string | null>(null)
  const [designExcelReady, setDesignExcelReady] = useState(false)
  const [isGeneratingDesigned, setIsGeneratingDesigned] = useState(false)

  const [showSettings, setShowSettings] = useState(false)
  const [layout, setLayout] = useState<LayoutConfig>({ ...DEFAULT_LAYOUT })
  const [singleGuestName, setSingleGuestName] = useState('')
  const [singleGuestCount, setSingleGuestCount] = useState(1)
  const [singleGuestClass, setSingleGuestClass] = useState<'vip' | 'normal'>('normal')
  const [showSingleGuestModal, setShowSingleGuestModal] = useState(false)
  const { mutate: generate, isPending, data, isError, error, reset } = useGenerateInvitations()
  const [localError, setLocalError] = useState<string | null>(null)
  const [requireRsvp, setRequireRsvp] = useState(false)
  const [designCount, setDesignCount] = useState(1)
  const [designTicketClass, setDesignTicketClass] = useState<'vip' | 'normal'>('normal')
  const [designInputMode, setDesignInputMode] = useState<'count' | 'names' | 'excel'>(() => {
    if (typeof window === 'undefined') return 'count'
    const saved = window.localStorage.getItem(designModeStorageKey)
    return saved === 'count' || saved === 'names' || saved === 'excel' ? (saved as any) : 'count'
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
  const selectedTemplate = templates.find((t) => t.id === designTemplateId)

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

      return true
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

  const isBatchRunning = isGeneratingDesigned || (!!designBatchId && (!designBatch || ['queued', 'generating_barcodes', 'rendering_images', 'generating_pdf', 'generating_zip'].includes(designBatch.status)))
  const isBatchFailed = !!designBatchId && designBatch && designBatch.status === 'failed'
  const isBatchReady = !!designBatchId && designBatch && designBatch.status === 'ready'

  useEffect(() => {
    if (!designBatchId || !designBatch) return
    if (designBatch.status === 'ready' && designBatch.result_pdf_url) {
      setDesignStatus('اكتمل التوليد ويمكنك تنزيل الملفات الآن')
      queryClient.invalidateQueries({ queryKey: ['invitations'] })
      queryClient.invalidateQueries({ queryKey: ['event-stats', event.id] })
    } else if (designBatch.status === 'failed') {
      setDesignStatus('فشلت عملية التوليد')
    } else {
      setDesignStatus(`حالة الدفعة: ${designBatch.status} · %${designBatch.progress}`)
    }
  }, [designBatchId, designBatch, event.id, queryClient])

  useEffect(() => {
    if (typeof window === 'undefined') return
    window.localStorage.setItem(sourceStorageKey, generationSource)
  }, [generationSource, sourceStorageKey])

  useEffect(() => {
    if (typeof window === 'undefined') return
    window.localStorage.setItem(`event-invitations-quick-mode:${event.id}`, quickInputMode)
  }, [quickInputMode, event.id])

  useEffect(() => {
    if (typeof window === 'undefined') return
    window.localStorage.setItem(`event-invitations-quick-manual:${event.id}`, JSON.stringify(quickManualGuests))
  }, [quickManualGuests, event.id])

  useEffect(() => {
    if (typeof window === 'undefined') return
    window.localStorage.setItem(`event-invitations-quick-dynamic-fields:${event.id}`, JSON.stringify(quickDynamicFields))
  }, [quickDynamicFields, event.id])

  useEffect(() => {
    if (typeof window === 'undefined') return
    window.localStorage.setItem(`event-invitations-design-manual:${event.id}`, JSON.stringify(designManualGuests))
  }, [designManualGuests, event.id])

  // Clear success messages and reset generation states when switching tabs
  useEffect(() => {
    reset()
    setLocalError(null)
    setDesignBatchId('')
    setDesignStatus(null)
  }, [generationSource, reset])

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

  // ── Fetch dynamic fields when designed template changes ──
  useEffect(() => {
    if (!designTemplateId) {
      setDynamicFields(BUILTIN_FIELDS)
      setDesignTemplateElements([])
      return
    }
    let cancelled = false
    templatesApi.getElements(designTemplateId).then((elements) => {
      if (cancelled) return
      setDesignTemplateElements(elements)
      const fields: DynamicField[] = []
      const seenKeys = new Set<string>()
      for (const el of elements) {
        if (el.element_type === 'guest_name') {
          const key = el.data_key || 'guest.name'
          if (!seenKeys.has(key)) {
            seenKeys.add(key)
            fields.push({ data_key: key, label: getCleanFieldLabel(key, el.element_type, el.label), element_type: el.element_type, required: true })
          }
        } else if (el.element_type === 'dynamic_text' && el.data_key) {
          if (!seenKeys.has(el.data_key)) {
            seenKeys.add(el.data_key)
            fields.push({ data_key: el.data_key, label: getCleanFieldLabel(el.data_key, el.element_type, el.label), element_type: el.element_type, required: false })
          }
        } else if (['event_date', 'event_time', 'event_location', 'seat_number', 'gate', 'hall', 'table_number'].includes(el.element_type)) {
          const key = el.data_key || `custom.${el.element_type}`
          if (!seenKeys.has(key)) {
            seenKeys.add(key)
            fields.push({ data_key: key, label: getCleanFieldLabel(key, el.element_type, el.label), element_type: el.element_type, required: false })
          }
        }
      }
      setDynamicFields(fields)
    }).catch(() => {
      if (!cancelled) {
        setDynamicFields(BUILTIN_FIELDS)
        setDesignTemplateElements([])
      }
    })
    return () => { cancelled = true }
  }, [designTemplateId])

  // ── Auto-map and validate when template dynamic fields load ──
  useEffect(() => {
    if (designExcelColumns.length > 0 && designExcelFile && dynamicFields.length > 0) {
      const mapping = { ...designColumnMapping }
      let changed = false
      for (const field of dynamicFields) {
        if (!mapping[field.data_key]) {
          const match = findDesignMappingMatch(field.data_key, field.label, designExcelColumns)
          if (match) {
            mapping[field.data_key] = match
            changed = true
          }
        }
      }
      if (changed) {
        setDesignColumnMapping(mapping)
      }
      validateDesignMapping(mapping)
    }
  }, [dynamicFields])

  // ── Inline Excel helpers ──
  const findDesignMappingMatch = (dataKey: string, label: string, columns: DesignExcelColumn[]): string | null => {
    const aliases = ALIAS_MAP[dataKey] || []
    const potentialMatches = [...aliases, label, dataKey]
    for (const col of columns) {
      const colLower = col.name.toLowerCase().trim()
      if (potentialMatches.some((alias) => colLower === alias.toLowerCase())) return col.name
    }
    for (const col of columns) {
      const colLower = col.name.toLowerCase().trim()
      if (potentialMatches.some((alias) => colLower.includes(alias.toLowerCase()) || alias.toLowerCase().includes(colLower))) return col.name
    }
    return null
  }

  const validateDesignMapping = (mapping: Record<string, string>) => {
    const errors: string[] = []
    for (const field of dynamicFields) {
      if (field.required && !mapping[field.data_key]) {
        errors.push(`حقل مطلوب: ${field.label}`)
      }
    }
    setDesignMappingErrors(errors)
    setDesignExcelReady(errors.length === 0)
  }

  const handleDesignExcelUpload = async (file: File | null) => {
    if (!file) return
    setLocalError(null)
    try {
      const buffer = await file.arrayBuffer()
      const workbook = XLSX.read(buffer, { type: 'array', cellDates: true, cellNF: true })
      const firstSheet = workbook.Sheets[workbook.SheetNames[0]]
      const rows = XLSX.utils.sheet_to_json<Record<string, string>>(firstSheet, { defval: '' })
      if (!rows.length) {
        setLocalError('الملف فارغ أو لا يحتوي على بيانات صالحة')
        return
      }
      const columnNames = Object.keys(rows[0])
      const columns: DesignExcelColumn[] = columnNames.map((name, index) => ({
        name, index,
        sampleValues: rows.slice(0, 3).map((row) => String(row[name] || '')),
      }))
      setDesignExcelFile(file)
      setDesignExcelColumns(columns)
      setDesignExcelRows(rows)
      const mapping: Record<string, string> = {}
      for (const field of dynamicFields) {
        const match = findDesignMappingMatch(field.data_key, field.label, columns)
        if (match) mapping[field.data_key] = match
      }
      setDesignColumnMapping(mapping)
      validateDesignMapping(mapping)
    } catch {
      setLocalError('تعذر قراءة الملف. استخدم ملف Excel بصيغة .xlsx')
    }
  }

  const handleDesignMappingChange = (dataKey: string, columnName: string) => {
    const newMapping = { ...designColumnMapping, [dataKey]: columnName }
    setDesignColumnMapping(newMapping)
    validateDesignMapping(newMapping)
  }

  const clearDesignExcel = () => {
    setDesignExcelFile(null)
    setDesignExcelColumns([])
    setDesignExcelRows([])
    setDesignColumnMapping({})
    setDesignMappingErrors([])
    setDesignExcelReady(false)
  }

  const handleGenerateDesignedFromExcel = async () => {
    if (!designTemplateId || !designExcelRows.length) return
    setIsGeneratingDesigned(true)
    setLocalError(null)
    setDesignStatus(null)
    setDesignBatchId('')
    try {
      const invitations: Array<{
        guest_name: string
        guest_count: number
        metadata: {
          imported_from: string
          custom_fields: Record<string, string>
          require_rsvp?: boolean
        }
      }> = []

      const guestNameCol = designColumnMapping['guest.name']

      for (const row of designExcelRows) {
        // Filter rows by the current batch ticket class (designTicketClass)
        const rowTicketClass = resolveTicketClass(row, designTicketClass)
        if (rowTicketClass !== designTicketClass) {
          continue
        }

        const guestName = resolveGuestName(row, guestNameCol)
        const invitationCount = resolveGuestCount(row)

        const customFields: Record<string, string> = {}
        for (const field of dynamicFields) {
          if (field.data_key !== 'guest.name') {
            const colName = designColumnMapping[field.data_key]
            if (colName && row[colName]) {
              customFields[field.data_key] = sanitizeArabicDigits(String(formatCellValue(row[colName])))
            }
          }
        }

        invitations.push({
          guest_name: guestName,
          guest_count: invitationCount,
          metadata: {
            imported_from: designExcelFile?.name || 'Excel',
            custom_fields: customFields,
            require_rsvp: requireRsvp,
          },
        })
      }

      if (!invitations.length) throw new Error('لم يتم إنشاء أي دعوات صالحة')

      setDesignStatus('جاري إرسال الطلب والتوليد...')
      const batch = await batchesApi.generateDesignedFast({
        event_id: event.id,
        template_id: designTemplateId,
        ticket_class: designTicketClass,
        invitations,
        layout: designedLayout,
        output_formats: ['pdf', 'zip'],
        barcode_format: 'qr',
        metadata: {
          template_name: designTemplateName || undefined,
          source: 'excel',
        },
      })

      setDesignBatchId(batch.id)
      setDesignStatus(`تم بدء التوليد المصمم (${invitations.length} دعوة)`)
    } catch (err: any) {
      setLocalError(err.response?.data?.detail || err.message || 'تعذر بدء التوليد المصمم')
    } finally {
      setIsGeneratingDesigned(false)
    }
  }

  const updateLayout = (patch: Partial<LayoutConfig>) =>
    setLayout((prev) => ({ ...prev, ...patch }))

  const downloadExcelTemplate = () => {
    if (generationSource === 'design' && designTemplateId) {
      // Custom Excel template for the selected design!
      const customKeys = new Set<string>()
      dynamicFields.forEach((field) => {
        const dk = field.data_key || ''
        if (dk && dk.trim()) {
          const key = dk.trim()
          if (!['اسم الضيف', 'guest_name', 'name', 'guest.name', 'عدد الدعوات', 'عدد الأشخاص', 'invitation_count', 'count', 'نوع التذكرة', 'ticket_class', 'class'].includes(key)) {
            customKeys.add(key)
          }
        }
      })

      const baseHeaders = ['اسم الضيف', 'عدد الدعوات', 'نوع التذكرة']
      const allHeaders = [...baseHeaders, ...Array.from(customKeys)]

      const dummyRow: Record<string, any> = {
        'اسم الضيف': 'محمد عبدالله العمري',
        'عدد الدعوات': 1,
        'نوع التذكرة': designTicketClass === 'vip' ? 'VIP' : 'normal'
      }
      customKeys.forEach((key) => {
        dummyRow[key] = `بيانات ${key}`
      })

      const workbook = XLSX.utils.book_new()
      const worksheet = XLSX.utils.json_to_sheet([dummyRow], { header: allHeaders })
      XLSX.utils.book_append_sheet(workbook, worksheet, 'المدعوين')

      // Guide tab to explain
      const guideRows = [
        { 'العمود': 'اسم الضيف', 'النوع': 'نص (إلزامي)', 'الوصف': 'الاسم الكامل للضيف المطبوع على البطاقة' },
        { 'العمود': 'عدد الدعوات', 'النوع': 'رقم (اختياري)', 'الوصف': 'عدد البطاقات المطلوب توليدها لهذا الضيف (الافتراضي 1)' },
        { 'العمود': 'نوع التذكرة', 'النوع': 'VIP أو normal (اختياري)', 'الوصف': 'فئة التذكرة الخاصة بالضيف (VIP أو عادي)' },
      ]
      customKeys.forEach((key) => {
        guideRows.push({
          'العمود': key,
          'النوع': 'نص (حسب التصميم)',
          'الوصف': `الحقل المخصص المربوط بـ "${key}" في التصميم الخاص بك`
        })
      })
      const guideWorksheet = XLSX.utils.json_to_sheet(guideRows)
      XLSX.utils.book_append_sheet(workbook, guideWorksheet, 'دليل تعبئة الحقول')

      XLSX.writeFile(workbook, `نموذج_دعوات_تصميم_${designTemplateName.replace(/\s+/g, '_') || 'مخصص'}.xlsx`)
      return
    }

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

  // Quick manual guests list helpers
  const addQuickManualGuest = () => {
    const name = quickFormName.trim()
    if (!name) {
      setLocalError('يرجى كتابة اسم الضيف')
      return
    }
    const customFields: Record<string, string> = {}
    quickDynamicFields.forEach((field) => {
      customFields[field] = quickFormCustomFields[field] || ''
    })

    setQuickManualGuests((prev) => [
      ...prev,
      {
        guest_name: name,
        invitation_count: quickFormCount,
        ticket_class: quickFormClass,
        custom_fields: customFields,
      },
    ])
    setQuickFormName('')
    setQuickFormCount(1)
    setQuickFormCustomFields({})
    setLocalError(null)
  }

  const deleteQuickManualGuest = (index: number) => {
    setQuickManualGuests((prev) => prev.filter((_, i) => i !== index))
  }

  const handleAddQuickField = () => {
    const fieldName = newQuickFieldName.trim()
    if (!fieldName) return
    if (['اسم الضيف', 'guest_name', 'name', 'عدد الأشخاص', 'عدد الدعوات', 'invitation_count', 'count', 'نوع التذكرة', 'ticket_class', 'class', 'الفئة', 'عدد المرافقين'].includes(fieldName)) {
      setLocalError('هذا الاسم محجوز كحقل أساسي')
      return
    }
    if (quickDynamicFields.includes(fieldName)) {
      setLocalError('الحقل موجود بالفعل')
      return
    }
    setQuickDynamicFields((prev) => [...prev, fieldName])
    setNewQuickFieldName('')
    setLocalError(null)
  }

  const removeQuickDynamicField = (fieldName: string) => {
    setQuickDynamicFields((prev) => prev.filter((f) => f !== fieldName))
    setQuickManualGuests((prev) => prev.map((g) => {
      if (!g.custom_fields) return g
      const updated = { ...g.custom_fields }
      delete updated[fieldName]
      return { ...g, custom_fields: updated }
    }))
  }

  // Design manual guests list helpers
  const addDesignManualGuest = () => {
    const name = designFormName.trim()
    if (!name) {
      setLocalError('يرجى كتابة اسم الضيف')
      return
    }
    
    // Copy the custom fields form state
    const customFields: Record<string, string> = {}
    for (const field of dynamicFields) {
      if (field.data_key !== 'guest.name') {
        customFields[field.data_key] = designFormCustomFields[field.data_key] || ''
      }
    }

    setDesignManualGuests((prev) => [
      ...prev,
      {
        guest_name: name,
        invitation_count: designFormCount,
        ticket_class: designTicketClass,
        custom_fields: customFields,
      },
    ])
    setDesignFormName('')
    setDesignFormCount(1)
    setDesignFormCustomFields({})
    setLocalError(null)
  }

  const deleteDesignManualGuest = (index: number) => {
    setDesignManualGuests((prev) => prev.filter((_, i) => i !== index))
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
    setGenerationSource('quick')
    setQuickInputMode('excel')
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
      const workbook = XLSX.read(buffer, { type: 'array', cellDates: true, cellNF: true })
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
              custom_fields[key] = String(formatCellValue(value))
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
          setGenerationSource('quick')
          setQuickInputMode('excel')
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
    if (generationSource === 'quick') {
      if (quickInputMode === 'excel' && excelImportedGuests.length === 0) return
      if (quickInputMode === 'names' && quickManualGuests.length === 0) return
      if (quickInputMode === 'manual' && vipCount === 0 && normalCount === 0) return
    } else {
      return
    }
    setLocalError(null)

    const invitations: FastInvitationItem[] = []
    if (quickInputMode === 'excel') {
      excelImportedGuests.forEach((guest) => {
        invitations.push({
          guest_name: guest.guest_name,
          ticket_class: guest.ticket_class,
          guest_count: guest.invitation_count,
          metadata: { require_rsvp: requireRsvp },
          ...guest.custom_fields,
        })
      })
    } else if (quickInputMode === 'names') {
      quickManualGuests.forEach((guest) => {
        invitations.push({
          guest_name: guest.guest_name,
          ticket_class: guest.ticket_class,
          guest_count: guest.invitation_count,
          metadata: { require_rsvp: requireRsvp },
          ...guest.custom_fields,
        })
      })
    } else {
      for (let i = 0; i < vipCount; i++)
        invitations.push({
          guest_name: `${guestPrefix} VIP ${i + 1}`,
          ticket_class: 'vip' as const,
          metadata: { require_rsvp: requireRsvp },
        })
      for (let i = 0; i < normalCount; i++)
        invitations.push({
          guest_name: `${guestPrefix} ${i + 1}`,
          ticket_class: 'normal' as const,
          metadata: { require_rsvp: requireRsvp },
        })
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

    setLocalError(null)
    setDesignStatus(null)
    setIsGeneratingDesigned(true)
    setDesignBatchId('')

    try {
      let invitations: Array<{
        guest_name: string
        guest_count: number
        metadata: {
          imported_from: string
          custom_fields: Record<string, string>
          require_rsvp?: boolean
        }
      }> = []

      if (designInputMode === 'names') {
        if (designManualGuests.length === 0) {
          throw new Error('القائمة فارغة. يرجى إضافة ضيف واحد على الأقل.')
        }
        invitations = designManualGuests.map((guest) => ({
          guest_name: guest.guest_name,
          guest_count: guest.invitation_count,
          metadata: {
            imported_from: 'Manual List',
            custom_fields: guest.custom_fields || {},
            require_rsvp: requireRsvp,
          },
        }))
      } else {
        if (designCount < 1) {
          throw new Error('عدد الدعوات يجب أن يكون 1 على الأقل')
        }
        invitations = Array.from({ length: designCount }, (_, i) => ({
          guest_name: `${guestPrefix} ${i + 1}`,
          guest_count: 1,
          metadata: {
            imported_from: 'Quick Mode',
            custom_fields: {},
            require_rsvp: requireRsvp,
          },
        }))
      }

      setDesignStatus('جاري إرسال الطلب والتوليد...')
      const batch = await batchesApi.generateDesignedFast({
        event_id: event.id,
        template_id: designTemplateId,
        ticket_class: designTicketClass,
        invitations,
        layout: designedLayout,
        output_formats: ['pdf', 'zip'],
        barcode_format: 'qr',
        metadata: {
          template_name: designTemplateName || undefined,
          source: designInputMode === 'names' ? 'names' : 'count',
        },
      })

      setDesignBatchId(batch.id)
      setDesignStatus(`تم بدء التوليد المصمم (${invitations.length} دعوة)`)
    } catch (err: any) {
      setLocalError(err.response?.data?.detail || err.message || 'تعذر بدء التوليد المصمم')
    } finally {
      setIsGeneratingDesigned(false)
    }
  }

  const importedVipCount = excelImportedGuests.reduce((sum, guest) => sum + (guest.ticket_class === 'vip' ? guest.invitation_count : 0), 0)
  const importedNormalCount = excelImportedGuests.reduce((sum, guest) => sum + (guest.ticket_class === 'normal' ? guest.invitation_count : 0), 0)

  const quickManualVipCount = quickManualGuests.reduce((sum, guest) => sum + (guest.ticket_class === 'vip' ? guest.invitation_count : 0), 0)
  const quickManualNormalCount = quickManualGuests.reduce((sum, guest) => sum + (guest.ticket_class === 'normal' ? guest.invitation_count : 0), 0)

  const plannedVipCount =
    generationSource === 'quick'
      ? quickInputMode === 'excel'
        ? importedVipCount
        : quickInputMode === 'names'
        ? quickManualVipCount
        : vipCount
      : 0
  
  const plannedNormalCount =
    generationSource === 'quick'
      ? quickInputMode === 'excel'
        ? importedNormalCount
        : quickInputMode === 'names'
        ? quickManualNormalCount
        : normalCount
      : 0

  const totalImportedGuests = excelImportedGuests.length
  const isFormValid =
    generationSource === 'quick'
      ? quickInputMode === 'names'
        ? quickManualGuests.length > 0 &&
          plannedVipCount <= remainingVip &&
          plannedNormalCount <= remainingNormal
        : quickInputMode === 'excel'
        ? excelImportedGuests.length > 0 &&
          plannedVipCount <= remainingVip &&
          plannedNormalCount <= remainingNormal
        : (vipCount > 0 || normalCount > 0) &&
          plannedVipCount <= remainingVip &&
          plannedNormalCount <= remainingNormal
      : false
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
              className={`inv-source-switch__btn ${generationSource === 'quick' ? 'inv-source-switch__btn--active' : ''}`}
              onClick={() => setGenerationSource('quick')}
            >
              <QrCode size={15} /> التوليد السريع (باركود فقط)
            </button>
            <button
              type="button"
              className={`inv-source-switch__btn ${generationSource === 'design' ? 'inv-source-switch__btn--active' : ''}`}
              onClick={() => setGenerationSource('design')}
            >
              <Sparkles size={15} /> تصميم كرت مخصص (ثيم الحفل)
            </button>
          </div>

          {generationSource === 'quick' && (
            <div className="inv-design-inner-tabs" style={{ marginTop: 8, marginBottom: 16 }}>
              <button
                type="button"
                className={`inv-design-inner-tab ${quickInputMode === 'manual' ? 'inv-design-inner-tab--active' : ''}`}
                onClick={() => setQuickInputMode('manual')}
              >
                <Users size={14} /> توليد بالعدد (تلقائي)
              </button>
              <button
                type="button"
                className={`inv-design-inner-tab ${quickInputMode === 'names' ? 'inv-design-inner-tab--active' : ''}`}
                onClick={() => setQuickInputMode('names')}
              >
                <Plus size={14} /> إدخال يدوي بالأسماء
              </button>
              <button
                type="button"
                className={`inv-design-inner-tab ${quickInputMode === 'excel' ? 'inv-design-inner-tab--active' : ''}`}
                onClick={() => setQuickInputMode('excel')}
              >
                <FileSpreadsheet size={14} /> استيراد أسماء من Excel
              </button>
            </div>
          )}

          {generationSource === 'quick' && quickInputMode === 'names' && (
            <div className="inv-import-card">
              <div className="inv-import-card__header">
                <div>
                  <strong>إدخال أسماء المدعوين يدوياً</strong>
                  <span>أدخل الأسماء مباشرة، وسيتم بناء قائمة بالمدعوين لإصدار بطاقاتهم دفعة واحدة.</span>
                </div>
              </div>

              {/* Dynamic Fields Management */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 12, marginBottom: 12, padding: 12, background: 'rgba(255,255,255,0.01)', borderRadius: 8, border: '1px solid rgba(255,255,255,0.04)' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <Database size={14} style={{ color: 'var(--color-primary)' }} />
                    <span style={{ fontSize: '13px', fontWeight: '600' }}>الحقول المخصصة النشطة</span>
                  </div>
                  
                  {/* Input to add a new custom field */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <input
                      type="text"
                      placeholder="اسم الحقل (مثال: الجهة، المنصب)"
                      value={newQuickFieldName}
                      onChange={(e) => setNewQuickFieldName(e.target.value)}
                      className="inv-input"
                      style={{ width: '180px', height: '32px', fontSize: '12px', padding: '0 8px' }}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault();
                          handleAddQuickField();
                        }
                      }}
                    />
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={handleAddQuickField}
                      style={{ height: '32px', padding: '0 12px', fontSize: '12px', display: 'flex', alignItems: 'center', gap: 4, borderRadius: '6px' }}
                    >
                      <Plus size={12} /> إضافة حقل
                    </button>
                  </div>
                </div>

                {quickDynamicFields.length > 0 ? (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 4 }}>
                    {quickDynamicFields.map((field) => (
                      <span key={field} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, background: 'rgba(var(--color-primary-rgb), 0.1)', border: '1px solid rgba(var(--color-primary-rgb), 0.2)', color: 'var(--color-primary)', padding: '2px 8px', borderRadius: '16px', fontSize: '11px' }}>
                        {field}
                        <button type="button" onClick={() => removeQuickDynamicField(field)} style={{ background: 'none', border: 'none', color: 'rgba(255,255,255,0.4)', cursor: 'pointer', display: 'flex', alignItems: 'center', padding: 0 }} title="حذف الحقل">
                          <X size={12} />
                        </button>
                      </span>
                    ))}
                  </div>
                ) : (
                  <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.4)', fontStyle: 'italic' }}>لا توجد حقول مخصصة حالياً. أضف حقولاً مثل "الجهة" أو "رقم الطاولة" لتعبئتها لكل ضيف.</div>
                )}
              </div>

              {/* Form to add a guest */}
              <div className="inv-design-tab-row" style={{ display: 'flex', flexDirection: 'column', gap: 16, background: 'rgba(255,255,255,0.02)', padding: 18, borderRadius: 12, marginBottom: 16 }}>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, width: '100%' }}>
                  <div style={{ flex: '2 1 250px' }}>
                    <label className="inv-label">اسم الضيف <span style={{ color: '#ef4444' }}>*</span></label>
                    <input
                      type="text"
                      value={quickFormName}
                      onChange={(e) => setQuickFormName(e.target.value)}
                      className="inv-input"
                      style={{ width: '100%' }}
                      placeholder="اكتب اسم الضيف الكامل..."
                    />
                  </div>
                  <div style={{ flex: '1 1 100px' }}>
                    <label className="inv-label">عدد المرافقين</label>
                    <input
                      type="number"
                      min={1}
                      value={quickFormCount}
                      onChange={(e) => setQuickFormCount(parseInt(e.target.value) || 1)}
                      className="inv-input"
                      style={{ width: '100%' }}
                    />
                  </div>
                  <div style={{ flex: '1 1 120px' }}>
                    <label className="inv-label">الفئة</label>
                    <select
                      value={quickFormClass}
                      onChange={(e) => setQuickFormClass(e.target.value as any)}
                      className="inv-input"
                      style={{ width: '100%' }}
                    >
                      <option value="normal">عادي</option>
                      <option value="vip">VIP</option>
                    </select>
                  </div>
                </div>

                {/* Render custom dynamic fields */}
                {quickDynamicFields.length > 0 && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, width: '100%', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: 12 }}>
                    {quickDynamicFields.map((fieldName) => (
                      <div key={fieldName} style={{ flex: '1 1 200px' }}>
                        <label className="inv-label">{fieldName}</label>
                        <input
                          type="text"
                          className="inv-input"
                          style={{ width: '100%' }}
                          value={quickFormCustomFields[fieldName] || ''}
                          onChange={(e) => setQuickFormCustomFields((prev) => ({
                            ...prev,
                            [fieldName]: e.target.value
                          }))}
                          placeholder={`بيانات ${fieldName}...`}
                        />
                      </div>
                    ))}
                  </div>
                )}

                <div style={{ display: 'flex', justifyContent: 'flex-end', width: '100%', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: 12 }}>
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={addQuickManualGuest}
                    style={{
                      height: '42px',
                      background: 'var(--color-primary)',
                      borderColor: 'var(--color-primary)',
                      color: '#fff',
                      padding: '0 24px',
                      borderRadius: '8px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      fontWeight: '600'
                    }}
                  >
                    <Plus size={16} /> إضافة الضيف للقائمة
                  </button>
                </div>
              </div>

              {/* Preview List Table */}
              {quickManualGuests.length > 0 ? (
                <div className="inv-design-preview" style={{ marginTop: 12 }}>
                  <div className="inv-design-preview__header">
                    <strong>قائمة الضيوف الحالية ({quickManualGuests.length} ضيوف)</strong>
                  </div>
                  <div className="inv-design-preview__table-wrap">
                    <table className="inv-design-preview__table">
                      <thead>
                        <tr>
                          <th>#</th>
                          <th>اسم الضيف</th>
                          <th>الفئة</th>
                          <th>عدد الأشخاص</th>
                          {quickDynamicFields.map((field) => (
                            <th key={field}>{field}</th>
                          ))}
                          <th style={{ width: 100 }}>إجراءات</th>
                        </tr>
                      </thead>
                      <tbody>
                        {quickManualGuests.map((guest, index) => (
                          <tr key={index}>
                            <td>{index + 1}</td>
                            <td>{guest.guest_name}</td>
                            <td>
                              <span className={`inv-design-template-card__type ${guest.ticket_class === 'vip' ? 'inv-design-template-card__type--dynamic' : ''}`} style={{ fontSize: '11px', padding: '2px 8px' }}>
                                {guest.ticket_class === 'vip' ? 'VIP' : 'عادي'}
                              </span>
                            </td>
                            <td>{guest.invitation_count}</td>
                            {quickDynamicFields.map((field) => (
                              <td key={field}>
                                {guest.custom_fields?.[field] || '—'}
                              </td>
                            ))}
                            <td>
                              <button
                                type="button"
                                className="inv-card-action-btn inv-card-action-btn--delete"
                                onClick={() => deleteQuickManualGuest(index)}
                                style={{ position: 'relative', border: '1px solid rgba(239, 68, 68, 0.3)', background: 'rgba(239, 68, 68, 0.08)', color: '#ef4444' }}
                                title="حذف"
                              >
                                <Trash2 size={13} />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                <div style={{ textAlign: 'center', padding: '30px 20px', border: '1px dashed var(--color-border)', borderRadius: 12, opacity: 0.6, fontSize: '13px' }}>
                  القائمة فارغة حالياً. ابدأ بإدخال اسم ضيف وإضافته للقائمة أعلاه.
                </div>
              )}
            </div>
          )}

          {generationSource === 'quick' && quickInputMode === 'manual' && <>
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
          </>}

          {generationSource === 'quick' && quickInputMode === 'excel' && (
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
            <div className="inv-import-card inv-design-card" style={{ position: 'relative' }}>
              {isBatchRunning && (
                <div className="inv-design-overlay">
                  <div className="inv-design-overlay__card">
                    <Loader2 size={44} className="inv-design-overlay__spin" />
                    <h3 className="inv-design-overlay__title">جاري توليد الدعوات المصممة</h3>
                    <p className="inv-design-overlay__desc">
                      {designStatus || 'يرجى الانتظار حتى اكتمال التوليد...'}
                    </p>
                    
                    {/* Sleek Progress Bar */}
                    <div className="inv-design-progress">
                      <div 
                        className="inv-design-progress__fill" 
                        style={{ width: `${designBatch?.progress || 0}%` }} 
                      />
                    </div>
                    <span className="inv-design-progress__pct">
                      %{designBatch?.progress || 0}
                    </span>
                    
                    {designBatch && (
                      <span className="inv-design-progress__sub">
                        تم معالجة {designBatch.count_done} من {designBatch.count_total} دعوة
                      </span>
                    )}
                  </div>
                </div>
              )}

              {isBatchReady && (
                <div className="inv-design-overlay inv-design-overlay--success">
                  <div className="inv-design-overlay__card">
                    <div className="inv-design-overlay__icon inv-design-overlay__icon--success">
                      <CheckCircle2 size={48} />
                    </div>
                    <h3 className="inv-design-overlay__title">تم التوليد بنجاح! 🎉</h3>
                    <p className="inv-design-overlay__desc">
                      تم توليد {designBatch.count_total} دعوة مصممة بنجاح في {((designBatch.duration_ms || 0) / 1000).toFixed(1)} ثانية.
                    </p>
                    
                    <div className="inv-design-overlay__actions">
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
                    
                    <button 
                      type="button" 
                      className="inv-design-overlay__close-btn"
                      onClick={() => {
                        setDesignBatchId('')
                        setDesignStatus(null)
                      }}
                    >
                      إغلاق النافذة
                    </button>
                  </div>
                </div>
              )}

              {isBatchFailed && (
                <div className="inv-design-overlay inv-design-overlay--error">
                  <div className="inv-design-overlay__card">
                    <div className="inv-design-overlay__icon inv-design-overlay__icon--error">
                      <AlertCircle size={48} />
                    </div>
                    <h3 className="inv-design-overlay__title">فشلت عملية التوليد</h3>
                    <p className="inv-design-overlay__desc">
                      {designBatch.error_message || 'حدث خطأ غير متوقع أثناء معالجة البطاقات.'}
                    </p>
                    
                    <button 
                      type="button" 
                      className="inv-design-overlay__close-btn inv-design-overlay__close-btn--error"
                      onClick={() => {
                        setDesignBatchId('')
                        setDesignStatus(null)
                      }}
                    >
                      إغلاق ومحاولة أخرى
                    </button>
                  </div>
                </div>
              )}

              {/* Header */}
              <div className="inv-import-card__header">
                <div>
                  <strong>تصميم مخصص للدعوات</strong>
                  <span>اختر نوع الدعوة والقالب، ثم ولّد ملفات PDF/ZIP جاهزة للطباعة.</span>
                </div>
              </div>

              {/* Sub-tabs selector for Design tab (top of design content) */}
              <div className="inv-design-inner-tabs" style={{ marginTop: 8, marginBottom: 16 }}>
                <button
                  type="button"
                  className={`inv-design-inner-tab ${designInputMode === 'count' ? 'inv-design-inner-tab--active' : ''}`}
                  onClick={() => setDesignInputMode('count')}
                >
                  <QrCode size={14} /> توليد بالعدد (تلقائي)
                </button>
                <button
                  type="button"
                  className={`inv-design-inner-tab ${designInputMode === 'names' ? 'inv-design-inner-tab--active' : ''}`}
                  onClick={() => setDesignInputMode('names')}
                >
                  <Plus size={14} /> إدخال يدوي بالأسماء
                </button>
                <button
                  type="button"
                  className={`inv-design-inner-tab ${designInputMode === 'excel' ? 'inv-design-inner-tab--active' : ''}`}
                  onClick={() => setDesignInputMode('excel')}
                >
                  <FileSpreadsheet size={14} /> استيراد بيانات من ملف Excel
                </button>
              </div>

              <div className="inv-design-body">
                {/* ═══ Section ① — Invitation Type ═══ */}
                <div className="inv-design-section">
                  <label className="inv-design-section__label">
                    <span className="inv-design-section__num">①</span> نوع الدعوات
                  </label>
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

                {/* ═══ Section ② — Template Selection ═══ */}
                <div className="inv-design-section">
                  <label className="inv-design-section__label">
                    <span className="inv-design-section__num">②</span> القالب ({designTicketClass === 'vip' ? 'VIP' : 'عادي'})
                  </label>
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
                      <QrCode size={28} style={{ opacity: 0.3 }} />
                      <p>لا توجد قوالب {designTicketClass === 'vip' ? 'VIP' : 'عادية'} بعد</p>
                      <span>افتح محرر التصميم لإنشاء قالب جديد</span>
                      <button
                        type="button"
                        className="inv-design-editor-btn"
                        style={{ marginTop: 12 }}
                        onClick={() => navigate(`/events/${event.id}/design?class=${designTicketClass}${designInputMode === 'excel' ? '&mode=excel' : ''}`)}
                      >
                        <Plus size={14} /> إنشاء قالب جديد
                      </button>
                    </div>
                  ) : (
                    <div className="inv-design-templates-grid">
                      {matchingDesignedTemplates.map(({ template: tpl, hasDynamic, dynamicCount }) => (
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
                            <div className="inv-design-template-card__actions-overlay">
                              <button type="button" className="inv-card-action-btn inv-card-action-btn--edit" onClick={(e) => { e.stopPropagation(); navigate(`/events/${event.id}/design?edit=${tpl.id}${designInputMode === 'excel' ? '&mode=excel' : ''}`) }} title="تحرير التصميم">
                                <Pencil size={14} />
                              </button>
                              <button type="button" className="inv-card-action-btn inv-card-action-btn--preview" onClick={async (e) => { e.stopPropagation(); await handlePreview(tpl) }} title="معاينة" disabled={previewMutation.isPending}>
                                {previewMutation.isPending && selectedTemplateForPreview?.id === tpl.id ? <Loader2 size={14} className="spin" /> : <Eye size={14} />}
                              </button>
                              <button type="button" className="inv-card-action-btn inv-card-action-btn--delete" onClick={(e) => { e.stopPropagation(); handleDeleteTemplate(tpl) }} title="حذف" disabled={deleteMutation.isPending}>
                                {deleteMutation.isPending && selectedTemplateForPreview?.id === tpl.id ? <Loader2 size={14} className="spin" /> : <Trash2 size={14} />}
                              </button>
                            </div>
                          </div>
                          <div className="inv-design-template-card__name">{tpl.name}</div>
                          <div className={`inv-design-template-card__type ${hasDynamic ? 'inv-design-template-card__type--dynamic' : ''}`}>
                            {hasDynamic ? <><Database size={10} /> {dynamicCount} حقل</> : <><QrCode size={10} /> QR</>}
                          </div>
                          {designTemplateId === tpl.id && (
                            <div className="inv-design-template-card__badge"><CheckCircle2 size={14} /></div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* ═══ Section ③ — Data Source ═══ */}
                <div className="inv-design-section">
                  <label className="inv-design-section__label">
                    <span className="inv-design-section__num">③</span> {designInputMode === 'count' ? 'تحديد عدد الدعوات' : designInputMode === 'names' ? 'إدخال بيانات الضيوف يدوياً' : 'تحميل بيانات الضيوف من Excel'}
                  </label>

                  {designInputMode === 'count' ? (
                    <div className="inv-design-count-panel">
                      <div className="inv-design-tab-row">
                        <div style={{ flex: 1 }}>
                          <label className="inv-label">عدد الدعوات</label>
                          <input type="number" min={1} max={10000} value={designCount} onChange={(e) => setDesignCount(parseInt(e.target.value) || 1)} className="inv-input" style={{ width: '100%' }} disabled={isPending} />
                        </div>
                        <button type="button" className="inv-design-editor-btn" onClick={() => navigate(`/events/${event.id}/design?mode=count`)}>
                          <Sparkles size={14} /> فتح محرر التصميم
                        </button>
                      </div>
                    </div>
                  ) : designInputMode === 'names' ? (
                    <div className="inv-design-excel-panel" style={{ padding: 20 }}>
                      {!designTemplateId ? (
                        <div className="inv-design-excel-notice">
                          <AlertCircle size={18} />
                          <span>يرجى اختيار قالب من الأعلى أولاً للبدء في إدخال أسماء وبيانات الضيوف المخصصة.</span>
                        </div>
                      ) : (
                        <>
                          <div className="inv-design-excel-header" style={{ marginBottom: 12 }}>
                            <div>
                              <strong>إدخال بيانات الضيوف يدوياً</strong>
                              <span>أدخل أسماء الضيوف وملأ بيانات التصميم مباشرة لتوليد كروتهم المخصصة.</span>
                            </div>
                          </div>

                          {/* Form to add a guest with dynamic fields */}
                          <div className="inv-design-tab-row" style={{ display: 'flex', flexDirection: 'column', gap: 16, background: 'rgba(255,255,255,0.02)', padding: 18, borderRadius: 12, marginBottom: 16 }}>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, width: '100%' }}>
                              <div style={{ flex: '2 1 250px' }}>
                                <label className="inv-label">اسم الضيف <span style={{ color: '#ef4444' }}>*</span></label>
                                <input
                                  type="text"
                                  value={designFormName}
                                  onChange={(e) => setDesignFormName(e.target.value)}
                                  className="inv-input"
                                  style={{ width: '100%' }}
                                  placeholder="اكتب اسم الضيف الكامل..."
                                />
                              </div>
                              <div style={{ flex: '1 1 100px' }}>
                                <label className="inv-label">عدد الدعوات</label>
                                <input
                                  type="number"
                                  min={1}
                                  value={designFormCount}
                                  onChange={(e) => setDesignFormCount(parseInt(e.target.value) || 1)}
                                  className="inv-input"
                                  style={{ width: '100%' }}
                                />
                              </div>
                            </div>

                            {/* Render custom dynamic fields */}
                            {dynamicFields.filter(f => f.data_key !== 'guest.name').length > 0 && (
                              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, width: '100%', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: 12 }}>
                                {dynamicFields.map((field) => {
                                  if (field.data_key === 'guest.name') return null
                                  return (
                                    <div key={field.data_key} style={{ flex: '1 1 200px' }}>
                                      <label className="inv-label">{field.label}</label>
                                      <input
                                        type="text"
                                        className="inv-input"
                                        style={{ width: '100%' }}
                                        value={designFormCustomFields[field.data_key] || ''}
                                        onChange={(e) => setDesignFormCustomFields((prev) => ({
                                          ...prev,
                                          [field.data_key]: e.target.value
                                        }))}
                                        placeholder={`بيانات ${field.label}...`}
                                      />
                                    </div>
                                  )
                                })}
                              </div>
                            )}

                            <div style={{ display: 'flex', justifyContent: 'flex-end', width: '100%', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: 12 }}>
                              <button
                                type="button"
                                className="btn btn-primary"
                                onClick={addDesignManualGuest}
                                style={{
                                  height: '42px',
                                  background: 'var(--color-primary)',
                                  borderColor: 'var(--color-primary)',
                                  color: '#fff',
                                  padding: '0 24px',
                                  borderRadius: '8px',
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: '6px',
                                  fontWeight: '600'
                                }}
                              >
                                <Plus size={16} /> إضافة الضيف للقائمة
                              </button>
                            </div>
                          </div>

                          {/* Preview List Table */}
                          {designManualGuests.length > 0 ? (
                            <div className="inv-design-preview" style={{ marginTop: 12 }}>
                              <div className="inv-design-preview__header">
                                <strong>قائمة الضيوف الحالية ({designManualGuests.length} ضيوف)</strong>
                              </div>
                              <div className="inv-design-preview__table-wrap">
                                <table className="inv-design-preview__table">
                                  <thead>
                                    <tr>
                                      <th>#</th>
                                      <th>اسم الضيف</th>
                                      <th>عدد الدعوات</th>
                                      {dynamicFields.map((f) => f.data_key !== 'guest.name' && <th key={f.data_key}>{f.label}</th>)}
                                      <th style={{ width: 100 }}>إجراءات</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {designManualGuests.map((guest, index) => (
                                      <tr key={index}>
                                        <td>{index + 1}</td>
                                        <td>{guest.guest_name}</td>
                                        <td>{guest.invitation_count}</td>
                                        {dynamicFields.map((f) => {
                                          if (f.data_key === 'guest.name') return null
                                          return (
                                            <td key={f.data_key}>
                                              {guest.custom_fields?.[f.data_key] || '—'}
                                            </td>
                                          )
                                        })}
                                        <td>
                                          <button
                                            type="button"
                                            className="inv-card-action-btn inv-card-action-btn--delete"
                                            onClick={() => deleteDesignManualGuest(index)}
                                            style={{ position: 'relative', border: '1px solid rgba(239, 68, 68, 0.3)', background: 'rgba(239, 68, 68, 0.08)', color: '#ef4444' }}
                                            title="حذف"
                                          >
                                            <Trash2 size={13} />
                                          </button>
                                        </td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            </div>
                          ) : (
                            <div style={{ textAlign: 'center', padding: '30px 20px', border: '1px dashed var(--color-border)', borderRadius: 12, opacity: 0.6, fontSize: '13px' }}>
                              القائمة فارغة حالياً. ابدأ بإدخال بيانات ضيف وإضافته للقائمة أعلاه.
                            </div>
                          )}
                        </>
                      )}
                    </div>
                  ) : (
                    <div className="inv-design-excel-panel">
                      {!designTemplateId ? (
                        <div className="inv-design-flow2-container" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                          <div className="inv-design-excel-notice">
                            <AlertCircle size={18} />
                            <span>يرجى اختيار قالب من الأعلى، أو البدء برفع ملف الـ Excel الخاص بك أولاً لتصميم قالب متناسق معه مباشرة.</span>
                          </div>
                          
                          <div className="inv-design-excel-upload" style={{ marginTop: '4px' }}>
                            <label className={`inv-design-excel-dropzone ${designExcelFile ? 'inv-design-excel-dropzone--done' : ''}`}>
                              <input 
                                type="file" 
                                accept=".xlsx,.xls,.csv" 
                                onClick={(e) => { e.currentTarget.value = '' }} 
                                onChange={async (e) => {
                                  const file = e.target.files?.[0]
                                  if (!file) return
                                  try {
                                    const buffer = await file.arrayBuffer()
                                    const workbook = XLSX.read(buffer, { type: 'array', cellDates: true, cellNF: true })
                                    const firstSheet = workbook.Sheets[workbook.SheetNames[0]]
                                    const rows = XLSX.utils.sheet_to_json<Record<string, unknown>>(firstSheet, { defval: '' })
                                    if (rows.length > 0) {
                                      const columnNames = Object.keys(rows[0])
                                      // Save columns in sessionStorage for the designer
                                      sessionStorage.setItem(`excel_cols_${event.id}`, JSON.stringify(columnNames))
                                      sessionStorage.setItem(`excel_name_${event.id}`, file.name)
                                      
                                      await handleDesignExcelUpload(file)
                                      setModalAlert({
                                        title: 'تم قراءة الملف بنجاح',
                                        message: `تم قراءة ${columnNames.length} أعمدة بنجاح من الملف. يمكنك الآن الانتقال لتصميم القالب مباشرة.`,
                                        type: 'success'
                                      })
                                    } else {
                                      setModalAlert({
                                        title: 'ملف فارغ',
                                        message: 'ملف Excel فارغ أو لا يحتوي على صفوف بيانات',
                                        type: 'error'
                                      })
                                    }
                                  } catch (err: any) {
                                    setModalAlert({
                                      title: 'خطأ في قراءة الملف',
                                      message: `خطأ في قراءة ملف الإكسل: ${err.message}`,
                                      type: 'error'
                                    })
                                  }
                                }} 
                                hidden 
                              />
                              {designExcelFile ? (
                                <>
                                  <CheckCircle2 size={28} style={{ color: '#10b981' }} />
                                  <span className="inv-design-excel-dropzone__name">{designExcelFile.name}</span>
                                  <span className="inv-design-excel-dropzone__hint">{designExcelRows.length} ضيف · انقر لتغيير الملف</span>
                                </>
                              ) : (
                                <>
                                  <Upload size={28} />
                                  <span className="inv-design-excel-dropzone__name">رفع ملف Excel أولاً لبدء التصميم</span>
                                  <span className="inv-design-excel-dropzone__hint">ملفات Excel (.xlsx) أو CSV (.csv) لربط أعمدتها بالتصميم مباشرة</span>
                                </>
                              )}
                            </label>
                            {designExcelFile && (
                              <button type="button" className="inv-design-excel-clear" onClick={clearDesignExcel}>
                                <X size={14} /> مسح الملف
                              </button>
                            )}
                          </div>

                          {designExcelFile && (
                            <div style={{ display: 'flex', justifyContent: 'center', marginTop: '4px' }}>
                              <button
                                type="button"
                                className="btn btn-primary"
                                onClick={() => {
                                  navigate(`/events/${event.id}/design?class=${designTicketClass}&mode=excel`)
                                }}
                                style={{
                                  background: 'var(--color-primary)',
                                  borderColor: 'var(--color-primary)',
                                  padding: '10px 20px',
                                  fontSize: '14px',
                                  fontWeight: '600',
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: '8px',
                                  borderRadius: '8px'
                                }}
                              >
                                <Sparkles size={16} />
                                البدء بتصميم قالب جديد باستخدام أعمدة هذا الملف
                              </button>
                            </div>
                          )}
                        </div>
                      ) : (
                        <>
                          <div className="inv-design-excel-header">
                            <div>
                              <strong>رفع بيانات الضيوف</strong>
                              <span>ملف Excel (.xlsx) يحتوي على أسماء الضيوف وبيانات التصميم</span>
                            </div>
                            <button type="button" className="inv-dl-btn inv-dl-btn--zip" onClick={downloadExcelTemplate}>
                              <Download size={15} /> تنزيل نموذج القالب
                            </button>
                          </div>

                          {dynamicFields.length > 1 && (
                            <div className="inv-design-fields-hint">
                              <span className="inv-design-fields-hint__title">📋 حقول التصميم المكتشفة:</span>
                              <div className="inv-design-fields-hint__list">
                                {dynamicFields.map((f) => (
                                  <span key={f.data_key} className={`inv-design-fields-hint__tag ${f.required ? 'inv-design-fields-hint__tag--req' : ''}`}>
                                    {f.label} {f.required && '*'}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}

                           {designExcelFile && designExcelColumns.length > 0 && (
                             <div className="inv-design-mapping-container-wrapper">
                               <div className="inv-design-mapping__header" style={{ marginBottom: 12 }}>
                                 <strong>تعيين الأعمدة للكرت المصمم</strong>
                                 <span>تم الكشف التلقائي عن {Object.keys(designColumnMapping).filter((k) => designColumnMapping[k]).length}/{dynamicFields.length} حقل</span>
                               </div>
                               {dynamicFields.length === 0 ? (
                                 <div className="inv-design-excel-notice" style={{ marginBottom: 12, background: 'rgba(59, 130, 246, 0.08)', color: '#60a5fa', borderColor: 'rgba(59, 130, 246, 0.18)', display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 14px', borderRadius: '8px' }}>
                                   <Info size={16} />
                                   <span>هذا القالب يحتوي على باركود وعناصر ثابتة فقط (لا يحتوي على نصوص ديناميكية). سيتم توليد البطاقات بالخلفية والباركود مباشرة لكل صف في ملف Excel.</span>
                                 </div>
                               ) : (
                                 designMappingErrors.length > 0 && (
                                   <div className="inv-design-mapping__errors" style={{ marginBottom: 12 }}>
                                     {designMappingErrors.map((err, i) => (
                                       <div key={i} className="inv-design-mapping__error-item"><AlertCircle size={14} /> {err}</div>
                                     ))}
                                   </div>
                                 )
                               )}
                               
                               <div className="inv-design-mapping-split">
                                 {/* Mapping Fields (Right in RTL) */}
                                 <div className="inv-design-mapping-form">
                                   <div className="inv-design-mapping__grid-vertical">
                                     {dynamicFields.map((field) => {
                                       const isHovered = hoveredFieldKey === field.data_key
                                       const mappedCol = designColumnMapping[field.data_key]
                                       const sampleVal = mappedCol ? designExcelRows[0]?.[mappedCol] : null

                                       return (
                                         <div 
                                           key={field.data_key} 
                                           className={`inv-design-mapping-card ${isHovered ? 'inv-design-mapping-card--hovered' : ''} ${mappedCol ? 'inv-design-mapping-card--mapped' : ''} ${field.required && !mappedCol ? 'inv-design-mapping-card--required-error' : ''}`}
                                           onMouseEnter={() => setHoveredFieldKey(field.data_key)}
                                           onMouseLeave={() => setHoveredFieldKey(null)}
                                         >
                                           <div className="inv-design-mapping-card-header">
                                             <label className="inv-design-mapping-card-label">
                                               {field.label}
                                               {field.required && <span className="inv-design-badge inv-design-badge--required">إلزامي للكرت</span>}
                                               {!field.required && <span className="inv-design-badge inv-design-badge--optional">اختياري</span>}
                                             </label>
                                             {mappedCol && <CheckCircle2 size={14} style={{ color: '#10b981' }} />}
                                           </div>
                                           <span className="inv-design-mapping-card-key">مفتاح الحقل: {field.data_key}</span>

                                           <select 
                                             value={mappedCol || ''} 
                                             onChange={(e) => handleDesignMappingChange(field.data_key, e.target.value)} 
                                             className="inv-input inv-design-mapping-select"
                                           >
                                             <option value="">— اختر عمود —</option>
                                             {designExcelColumns.map((col) => (
                                               <option key={col.name} value={col.name}>{col.name} {col.sampleValues[0] ? `(${col.sampleValues[0]})` : ''}</option>
                                             ))}
                                           </select>

                                           {sampleVal && (
                                             <div className="inv-design-mapping-card-preview">
                                               <span className="preview-label">القيمة الأولى للمعاينة:</span>
                                               <span className="preview-val">{sampleVal}</span>
                                             </div>
                                           )}
                                         </div>
                                       )
                                     })}
                                   </div>
                                 </div>

                                 {/* Live Card Preview (Left in RTL) */}
                                 <div className="inv-design-card-preview-panel">
                                   <div className="preview-panel-title">معاينة كرت الدعوة التفاعلية</div>
                                   <div className="preview-panel-subtitle">مرر الماوس فوق أي حقل لرؤية موقعه على التصميم</div>

                                   {selectedTemplate && (
                                     <div 
                                       className="card-preview-container"
                                       style={{
                                         aspectRatio: selectedTemplate.orientation === 'landscape' || (selectedTemplate.width_px || 1080) > (selectedTemplate.height_px || 1920) 
                                           ? '1.414 / 1' 
                                           : '1 / 1.414',
                                         backgroundColor: selectedTemplate.background_color || '#111827',
                                         backgroundImage: selectedTemplate.background_url ? `url(${selectedTemplate.background_url})` : 'none',
                                       }}
                                     >
                                       {/* Render design overlay elements */}
                                       {designTemplateElements
                                         .filter(el => el.is_visible !== false)
                                         .map((el) => {
                                           const isDynamic = el.element_type === 'guest_name' || el.element_type === 'dynamic_text' || ['event_date', 'event_time', 'event_location', 'seat_number', 'gate', 'hall', 'table_number'].includes(el.element_type)
                                           
                                           const key = el.data_key || (el.element_type === 'guest_name' ? 'guest.name' : `custom.${el.element_type}`)
                                           const mappedCol = designColumnMapping[key]
                                           
                                           let displayText = ''
                                           if (el.element_type === 'qr_code' || el.element_type === 'barcode') {
                                             displayText = el.element_type === 'qr_code' ? 'QR Code' : 'Barcode'
                                           } else if (isDynamic) {
                                             if (mappedCol) {
                                               displayText = designExcelRows[0]?.[mappedCol] || el.label || key
                                             } else {
                                               displayText = `{${getCleanFieldLabel(key, el.element_type, el.label)}}`
                                             }
                                           } else {
                                             displayText = el.static_content || el.label || ''
                                           }

                                           const isActive = hoveredFieldKey === key

                                           return (
                                             <div
                                               key={el.id}
                                               className={`card-preview-element ${isDynamic ? 'card-preview-element--dynamic' : ''} ${mappedCol ? 'card-preview-element--mapped' : ''} ${isActive ? 'card-preview-element--active' : ''} ${el.element_type === 'qr_code' || el.element_type === 'barcode' ? 'card-preview-element--qr' : ''}`}
                                               style={{
                                                 left: `${el.x * 100}%`,
                                                 top: `${el.y * 100}%`,
                                                 width: `${el.width * 100}%`,
                                                 height: `${el.height * 100}%`,
                                                 transform: `rotate(${el.rotation || 0}deg)`,
                                                 fontFamily: el.font_family || 'Cairo',
                                                 fontSize: `${Math.max(7, (el.font_size || 14) * 0.16)}px`,
                                                 color: el.font_color || '#ffffff',
                                                 fontWeight: el.font_weight || 'normal',
                                                 display: 'flex',
                                                 alignItems: 'center',
                                                 justifyContent: el.text_align === 'left' ? 'flex-start' : el.text_align === 'right' ? 'flex-end' : 'center',
                                                 textAlign: el.text_align as any || 'center',
                                                 pointerEvents: isDynamic ? 'auto' : 'none',
                                               }}
                                               onMouseEnter={() => isDynamic && setHoveredFieldKey(key)}
                                               onMouseLeave={() => isDynamic && setHoveredFieldKey(null)}
                                             >
                                               {el.element_type === 'qr_code' && (
                                                 <div className="preview-qr-box">
                                                   <span>QR</span>
                                                 </div>
                                               )}
                                               {el.element_type === 'barcode' && (
                                                 <div className="preview-barcode-box">
                                                   <span>||||</span>
                                                 </div>
                                               )}
                                               {el.element_type !== 'qr_code' && el.element_type !== 'barcode' && (
                                                 <span className="truncate-text">{displayText}</span>
                                               )}
                                             </div>
                                           )
                                         })}
                                     </div>
                                   )}
                                 </div>
                               </div>
                             </div>
                           )}

                          <div className="inv-design-excel-upload">
                            <label className={`inv-design-excel-dropzone ${designExcelFile ? 'inv-design-excel-dropzone--done' : ''}`}>
                              <input type="file" accept=".xlsx,.xls,.csv" onClick={(e) => { e.currentTarget.value = '' }} onChange={(e) => handleDesignExcelUpload(e.target.files?.[0] ?? null)} hidden />
                              {designExcelFile ? (
                                <>
                                  <CheckCircle2 size={28} />
                                  <span className="inv-design-excel-dropzone__name">{designExcelFile.name}</span>
                                  <span className="inv-design-excel-dropzone__hint">{designExcelRows.length} ضيف · انقر لتغيير الملف</span>
                                </>
                              ) : (
                                <>
                                  <Upload size={28} />
                                  <span className="inv-design-excel-dropzone__name">اسحب الملف هنا أو انقر للاختيار</span>
                                  <span className="inv-design-excel-dropzone__hint">ملفات Excel (.xlsx) أو CSV (.csv)</span>
                                </>
                              )}
                            </label>
                            {designExcelFile && (
                              <button type="button" className="inv-design-excel-clear" onClick={clearDesignExcel}>
                                <X size={14} /> مسح الملف
                              </button>
                            )}
                          </div>

                          {designExcelFile && designExcelColumns.length > 0 && dynamicFields.length > 0 && (
                            <div className="inv-design-mapping">
                              <div className="inv-design-mapping__header">
                                <strong>تعيين الأعمدة</strong>
                                <span>تم الكشف التلقائي عن {Object.keys(designColumnMapping).filter((k) => designColumnMapping[k]).length}/{dynamicFields.length} حقل</span>
                              </div>
                              {designMappingErrors.length > 0 && (
                                <div className="inv-design-mapping__errors">
                                  {designMappingErrors.map((err, i) => (
                                    <div key={i} className="inv-design-mapping__error-item"><AlertCircle size={14} /> {err}</div>
                                  ))}
                                </div>
                              )}
                              <div className="inv-design-mapping__grid">
                                {dynamicFields.map((field) => (
                                  <div key={field.data_key} className="inv-design-mapping__item">
                                    <label className="inv-design-mapping__label">
                                      {field.label}
                                      {field.required && <span style={{ color: '#ef4444', marginRight: 4 }}>*</span>}
                                      {designColumnMapping[field.data_key] && <CheckCircle2 size={14} style={{ color: '#10b981' }} />}
                                    </label>
                                    <select value={designColumnMapping[field.data_key] || ''} onChange={(e) => handleDesignMappingChange(field.data_key, e.target.value)} className="inv-input">
                                      <option value="">— اختر عمود —</option>
                                      {designExcelColumns.map((col) => (
                                        <option key={col.name} value={col.name}>{col.name} {col.sampleValues[0] ? `(${col.sampleValues[0]})` : ''}</option>
                                      ))}
                                    </select>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {designExcelReady && designExcelRows.length > 0 && (
                            <div className="inv-design-preview">
                              <div className="inv-design-preview__header">
                                <strong>معاينة البيانات</strong>
                                <span>{designExcelRows.length} ضيف</span>
                              </div>
                              <div className="inv-design-preview__table-wrap">
                                <table className="inv-design-preview__table">
                                  <thead>
                                    <tr>
                                      <th>#</th>
                                      {dynamicFields.map((f) => <th key={f.data_key}>{f.label}</th>)}
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {designExcelRows.slice(0, 5).map((row, i) => (
                                      <tr key={i}>
                                        <td style={{ opacity: 0.5, fontFamily: 'var(--font-en)' }}>{i + 1}</td>
                                        {dynamicFields.map((f) => {
                                          const colName = designColumnMapping[f.data_key]
                                          return <td key={f.data_key}>{colName ? (row[colName] || '—') : '—'}</td>
                                        })}
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                                {designExcelRows.length > 5 && (
                                  <div className="inv-design-preview__more">... و {designExcelRows.length - 5} ضيف آخر</div>
                                )}
                              </div>
                              <div className="inv-design-preview__success">
                                <CheckCircle2 size={16} /> جميع البيانات جاهزة للتوليد
                              </div>
                            </div>
                          )}
                        </>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* RSVP Toggle for Design Mode */}
              {designTemplateId && (
                <div 
                  className={`toggle-row ${requireRsvp ? 'toggle-row--on' : ''}`} 
                  onClick={() => setRequireRsvp(!requireRsvp)}
                  style={{ marginTop: '20px', marginBottom: '8px' }}
                >
                  <div className="toggle-row-info">
                    <h4 style={{ margin: 0, fontSize: '14px', fontWeight: '600', color: '#fff' }}>تفعيل ميزة تأكيد الحضور (RSVP)</h4>
                    <p style={{ margin: '4px 0 0 0', fontSize: '12px', color: 'rgba(255,255,255,0.5)' }}>عند تفعيلها، سيُطلب من الضيوف تأكيد حضورهم أولاً لتنتقل الدعوات للدعوات النهائية.</p>
                  </div>
                  <div className={`toggle-switch ${requireRsvp ? 'toggle-switch--on' : ''}`}>
                    <div className="toggle-switch__thumb" />
                  </div>
                </div>
              )}

              {/* ═══ Generate Button ═══ */}
              {designInputMode === 'count' ? (
                <button type="button" className="inv-generate-btn" onClick={handleGenerateDesigned} disabled={isGeneratingDesigned || !designTemplateId} style={{ marginTop: 12 }}>
                  <Printer size={18} /> {isGeneratingDesigned ? 'جاري التوليد...' : `بدء التوليد (${designCount} دعوة)`}
                </button>
              ) : designInputMode === 'names' ? (
                designTemplateId && designManualGuests.length > 0 && (
                  <button type="button" className="inv-generate-btn" onClick={handleGenerateDesigned} disabled={isGeneratingDesigned} style={{ marginTop: 12 }}>
                    <Printer size={18} /> {isGeneratingDesigned ? 'جاري التوليد...' : `بدء التوليد (${designManualGuests.length} دعوة)`}
                  </button>
                )
              ) : (
                designTemplateId && designExcelReady && designExcelRows.length > 0 && (
                  <button type="button" className="inv-generate-btn" onClick={handleGenerateDesignedFromExcel} disabled={isGeneratingDesigned} style={{ marginTop: 12 }}>
                    <Printer size={18} /> {isGeneratingDesigned ? 'جاري التوليد...' : `بدء التوليد (${designExcelRows.length} دعوة)`}
                  </button>
                )
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
            <>
              {/* RSVP Toggle */}
              <div 
                className={`toggle-row ${requireRsvp ? 'toggle-row--on' : ''}`} 
                onClick={() => setRequireRsvp(!requireRsvp)}
                style={{ marginBottom: '16px' }}
              >
                <div className="toggle-row-info">
                  <h4 style={{ margin: 0, fontSize: '14px', fontWeight: '600', color: '#fff' }}>تفعيل ميزة تأكيد الحضور (RSVP)</h4>
                  <p style={{ margin: '4px 0 0 0', fontSize: '12px', color: 'rgba(255,255,255,0.5)' }}>عند تفعيلها، سيُطلب من الضيوف تأكيد حضورهم أولاً لتنتقل الدعوات للدعوات النهائية.</p>
                </div>
                <div className={`toggle-switch ${requireRsvp ? 'toggle-switch--on' : ''}`}>
                  <div className="toggle-switch__thumb" />
                </div>
              </div>

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
            </>
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

      {modalAlert && (
        <div className="inv-quick-modal-overlay" role="dialog" aria-modal="true" style={{ zIndex: 11000 }}>
          <div className="inv-quick-modal" style={{ width: '400px', padding: '20px' }}>
            <div className="inv-quick-modal__header" style={{ marginBottom: '12px' }}>
              <div>
                <h3 style={{
                  fontSize: '18px',
                  fontWeight: 'bold',
                  color: modalAlert.type === 'success' ? '#10b981' : modalAlert.type === 'error' ? '#ef4444' : '#3b82f6',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px'
                }}>
                  {modalAlert.type === 'success' ? '✓' : modalAlert.type === 'error' ? '⚠' : 'ℹ'} {modalAlert.title}
                </h3>
              </div>
            </div>
            <div className="inv-quick-modal__body" style={{ fontSize: '13px', color: 'rgba(255, 255, 255, 0.7)', lineHeight: '1.6', marginBottom: '16px' }}>
              {modalAlert.message}
            </div>
            <div className="inv-quick-modal__actions" style={{ marginTop: '12px' }}>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => setModalAlert(null)}
                style={{
                  width: '100%',
                  justifyContent: 'center',
                  background: modalAlert.type === 'success' ? '#10b981' : modalAlert.type === 'error' ? '#ef4444' : 'var(--color-primary)',
                  borderColor: modalAlert.type === 'success' ? '#10b981' : modalAlert.type === 'error' ? '#ef4444' : 'var(--color-primary)',
                  color: '#fff',
                  padding: '10px',
                  fontWeight: '600'
                }}
              >
                موافق
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
