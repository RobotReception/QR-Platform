import http from '@services/http/client'

export interface BatchLayoutConfig {
  page_size: 'A4' | 'Letter' | 'custom'
  orientation: 'portrait' | 'landscape'
  rows: number
  cols: number
  margin_top_mm: number
  margin_bottom_mm: number
  margin_left_mm: number
  margin_right_mm: number
  gap_x_mm: number
  gap_y_mm: number
  barcode_size_px: number | null
  barcode_size_mode: 'fit' | 'contain'
  show_code_text: boolean
  show_guest_name: boolean
  caption_field: 'guest_name' | 'code' | 'none'
  dpi: number
  card_per_page: boolean
  custom_width_mm?: number | null
  custom_height_mm?: number | null
  barcode_render: 'svg' | 'png'
  cell_padding_mm: number
}

export interface BatchCreateRequest {
  event_id: string
  template_id?: string | null
  mode: 'quick' | 'designed'
  ticket_class: 'vip' | 'normal'
  output_formats?: string[]
  barcode_format?: 'qr' | 'barcode128'
  layout: BatchLayoutConfig
  invitation_ids?: string[]
  metadata?: Record<string, any>
}

export interface BatchRead {
  id: string
  tenant_id: string
  event_id: string
  template_id: string | null
  mode: string
  ticket_class: string
  count_total: number
  count_done: number
  count_failed: number
  layout_json: Record<string, any> | null
  output_formats: string[]
  barcode_format: string
  status: string
  progress: number
  error_message: string | null
  result_pdf_url: string | null
  result_zip_url: string | null
  duration_ms?: number
  created_at: string
  updated_at: string
}

export const batchesApi = {
  create: (data: BatchCreateRequest) =>
    http.post<BatchRead>('/batches', data).then((r) => r.data),

  start: (batchId: string) =>
    http.post<{ message: string; batch_id: string; status: string }>(`/batches/${batchId}/start`).then((r) => r.data),

  get: (batchId: string) =>
    http.get<BatchRead>(`/batches/${batchId}`).then((r) => r.data),

  generateDesignedFast: (data: {
    event_id: string
    template_id: string
    ticket_class: 'vip' | 'normal'
    invitations: Array<{
      guest_name: string
      guest_count: number
      metadata: {
        imported_from: string
        custom_fields: Record<string, string>
      }
    }>
    layout: BatchLayoutConfig
    output_formats?: string[]
    barcode_format?: string
    metadata?: Record<string, any>
  }) =>
    http.post<BatchRead>('/batches/generate-designed-fast', data).then((r) => r.data),
}