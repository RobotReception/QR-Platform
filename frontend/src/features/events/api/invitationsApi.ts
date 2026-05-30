import http from '@services/http/client'

/* ── Layout Config ── */

export interface LayoutConfig {
  page_size: 'A4' | 'Letter';
  orientation: 'portrait' | 'landscape';
  rows: number;
  cols: number;
  margin_top_mm: number;
  margin_bottom_mm: number;
  margin_left_mm: number;
  margin_right_mm: number;
  gap_x_mm: number;
  gap_y_mm: number;
  barcode_size_px: number | null;  // null = auto-calculate
  show_code_text: boolean;
  show_guest_name: boolean;
}

export const DEFAULT_LAYOUT: LayoutConfig = {
  page_size: 'A4',
  orientation: 'portrait',
  rows: 5,
  cols: 5,
  margin_top_mm: 10,
  margin_bottom_mm: 10,
  margin_left_mm: 10,
  margin_right_mm: 10,
  gap_x_mm: 2,
  gap_y_mm: 2,
  barcode_size_px: null,
  show_code_text: false,
  show_guest_name: false,
}

/* ── Request / Response Models ── */

export interface FastInvitationItem {
  guest_name?: string;
  ticket_class: 'vip' | 'normal';
}

export interface FastInvitationRequest {
  event_id: string;
  invitations: FastInvitationItem[];
  layout_config?: Partial<LayoutConfig>;
  generate_zip: boolean;
  generate_pdf: boolean;
  upload_individual_barcodes?: boolean;
}

export interface FastGenerationResponse {
  success: boolean;
  total_invitations: number;
  generation_time_ms: number;
  pdf_url?: string;
  zip_url?: string;
  pdf_size_mb?: number;
  zip_size_mb?: number;
  error_message?: string;
}

export interface DownloadUrlResponse {
  download_url: string;
}

export interface GenerationHistoryItem {
  id: string;
  total_invitations: number;
  vip_count: number;
  normal_count: number;
  generated_at: string | null;
  pdf_url: string | null;
  zip_url: string | null;
}

export interface InvitationRead {
  id: string;
  tenant_id?: string;
  event_id?: string;
  token?: string;
  guest_name?: string | null;
  guest_whatsapp?: string | null;
  guest_phone?: string | null;
  guest_email?: string | null;
  ticket_class?: 'vip' | 'normal';
  status?: string;
  barcode_png_url?: string | null;
  barcode_svg_url?: string | null;
  pdf_url?: string | null;
  zip_url?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface DeleteGenerationResponse {
  success: boolean;
  deleted_invitations: number;
  deleted_files: number;
}

/* ── API Client ── */

export const invitationsApi = {
  generateFast: (payload: FastInvitationRequest) =>
    http.post<FastGenerationResponse>('/fast-invitations/generate', payload).then((r) => r.data),

  getEventPdfUrl: (eventId: string) =>
    http.get<DownloadUrlResponse>(`/fast-invitations/download/${eventId}/pdf`).then((r) => r.data),

  getEventZipUrl: (eventId: string) =>
    http.get<DownloadUrlResponse>(`/fast-invitations/download/${eventId}/zip`).then((r) => r.data),

  getGenerationHistory: (eventId: string) =>
    http.get<GenerationHistoryItem[]>(`/fast-invitations/history/${eventId}`).then((r) => r.data),

  getGenerationOperationDetails: (eventId: string, operationId: string) =>
    http.get<InvitationRead[]>(`/fast-invitations/history/${eventId}/${operationId}`).then((r) => r.data),

  deleteGenerationOperation: (eventId: string, operationId: string) =>
    http.delete<DeleteGenerationResponse>(`/fast-invitations/history/${eventId}/${operationId}`).then((r) => r.data),
}
