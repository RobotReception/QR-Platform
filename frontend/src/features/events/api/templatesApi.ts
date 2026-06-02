import http from '@services/http/client'

export interface AssetRead {
  id: string
  template_id: string
  asset_type: string
  file_url: string
  file_name: string | null
  file_size: number | null
  mime_type: string | null
  created_at: string
}

export type TemplateType = 'quick' | 'designed'
export type TemplateElementType =
  | 'guest_name'
  | 'guest_count'
  | 'event_title'
  | 'event_date'
  | 'event_time'
  | 'event_location'
  | 'qr_code'
  | 'barcode'
  | 'seat_number'
  | 'gate'
  | 'hall'
  | 'table_number'
  | 'custom_text'
  | 'dynamic_text'
  | 'image'

export interface TemplateRead {
  id: string
  tenant_id: string
  event_id: string | null
  name: string
  template_type: TemplateType
  ticket_class: string
  width_px: number | null
  height_px: number | null
  orientation: string | null
  background_url: string | null
  background_color: string | null
  quick_style: Record<string, any> | null
  is_default: boolean
  is_active: boolean
  metadata: Record<string, any> | null
  created_at: string
  updated_at: string
}

export interface BackgroundInspectResponse {
  width_px: number
  height_px: number
  mime_type?: string
  file_size: number
  preview_data_url?: string
}

export interface TemplateElementRead {
  id: string
  template_id: string
  element_type: TemplateElementType
  label: string | null
  data_key: string | null
  x: number
  y: number
  width: number
  height: number
  rotation: number
  font_family: string | null
  font_size: number | null
  font_weight: string | null
  font_color: string | null
  text_align: string | null
  text_direction: string | null
  line_height: number | null
  letter_spacing: number | null
  qr_size: number | null
  qr_color: string | null
  qr_bg_color: string | null
  qr_error_level: string | null
  static_content: string | null
  is_visible: boolean
  z_index: number
  sort_order: number
  slot_index: number | null
  created_at: string
}

export interface TemplateCreateRequest {
  event_id?: string
  name: string
  template_type?: TemplateType
  ticket_class?: 'vip' | 'normal'
  width_px?: number
  height_px?: number
  orientation?: 'portrait' | 'landscape'
  background_url?: string | null
  background_color?: string
  quick_style?: Record<string, any>
  is_default?: boolean
  metadata?: Record<string, any>
}

export interface TemplateElementCreateRequest {
  element_type: TemplateElementType
  label?: string | null
  data_key?: string | null
  x?: number
  y?: number
  width?: number
  height?: number
  rotation?: number
  font_family?: string
  font_size?: number
  font_weight?: string
  font_color?: string
  text_align?: string
  text_direction?: string
  line_height?: number
  letter_spacing?: number
  qr_size?: number
  qr_color?: string
  qr_bg_color?: string
  qr_error_level?: string
  static_content?: string | null
  is_visible?: boolean
  z_index?: number
  sort_order?: number
  slot_index?: number | null
}

export const templatesApi = {
  list: (eventId: string) =>
    http.get<TemplateRead[]>('/templates', { params: { event_id: eventId } }).then((r) => r.data),

  create: (data: TemplateCreateRequest) =>
    http.post<TemplateRead>('/templates', data).then((r) => r.data),

  uploadBackground: (templateId: string, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return http.post<{ background_url: string; file_size: number; mime_type?: string; width_px: number; height_px: number }>(`/templates/${templateId}/background`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then((r) => r.data)
  },

  uploadAsset: (templateId: string, file: File, assetType: string = 'overlay') => {
    const formData = new FormData()
    formData.append('file', file)
    return http.post<AssetRead>(`/templates/${templateId}/assets?asset_type=${assetType}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then((r) => r.data)
  },

  inspectBackground: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return http.post<BackgroundInspectResponse>('/templates/background/inspect', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then((r) => r.data)
  },

  replaceElements: (templateId: string, elements: TemplateElementCreateRequest[]) =>
    http.put<TemplateElementRead[]>(`/templates/${templateId}/elements`, elements).then((r) => r.data),

  getElements: (templateId: string) =>
    http.get<TemplateElementRead[]>(`/templates/${templateId}/elements`).then((r) => r.data),

  listFonts: () =>
    http.get<{ value: string; label: string }[]>('/templates/fonts').then((r) => r.data),

  uploadFont: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return http.post<{ status: string; font_family: string }>('/templates/fonts/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then((r) => r.data)
  },
}
