/**
 * checkinApi.ts
 * API layer for the Check-in feature.
 */
import http from '@services/http/client'

export interface CheckinRequest {
  token: string
  event_id?: string
  gate_id?: string
  scan_method?: string
  device_info?: string
}

export interface CheckinResponse {
  invitation_id: string | null
  result: string
  guest_name: string | null
  ticket_class: string | null
  event_title: string | null
  checkin_count: number
  guest_count: number
  message: string
}

export interface CheckinRecord {
  id: string
  invitation_id: string
  event_id: string
  gate_id: string | null
  result: string
  scanned_by: string | null
  scan_method: string | null
  created_at: string
}

export interface LiveStats {
  stats: {
    checked_in: number
    vip_checked_in: number
    normal_checked_in: number
    total_valid: number
    total_vip: number
    total_normal: number
  }
  recent_checkins: {
    created_at: string
    result: string
    guest_name: string | null
    ticket_class: string | null
    scan_method: string | null
  }[]
}

export const checkinKeys = {
  history: (eventId: string) => ['checkin', 'history', eventId] as const,
  live: (eventId: string) => ['checkin', 'live', eventId] as const,
}

export const checkinAPI = {
  scan: (data: CheckinRequest) =>
    http.post<CheckinResponse>('/checkin/scan', data).then((r) => r.data),

  manual: (invitationId: string, gateId?: string) =>
    http
      .post<CheckinResponse>('/checkin/manual', null, {
        params: { invitation_id: invitationId, gate_id: gateId },
      })
      .then((r) => r.data),

  history: (eventId?: string, result?: string) =>
    http
      .get<CheckinRecord[]>('/checkin/history', {
        params: { event_id: eventId, result },
      })
      .then((r) => r.data),

  liveStats: (eventId: string) =>
    http.get<LiveStats>(`/checkin/live/${eventId}`).then((r) => r.data),
}
