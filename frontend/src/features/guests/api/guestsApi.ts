/**
 * guestsApi.ts
 * API layer for Guests feature.
 */
import http from '@services/http/client'
import type { Guest, GuestCreateRequest, GuestUpdateRequest } from '../types'

export const guestKeys = {
  all: (tenantId: string) => ['guests', tenantId] as const,
  list: (tenantId: string, search?: string) => ['guests', tenantId, 'list', search] as const,
  detail: (tenantId: string, id: string) => ['guests', tenantId, 'detail', id] as const,
}

export const guestsAPI = {
  list: (search?: string) =>
    http.get<Guest[]>('/guests', { params: search ? { search } : undefined }).then((r) => r.data),

  get: (id: string) =>
    http.get<Guest>(`/guests/${id}`).then((r) => r.data),

  create: (data: GuestCreateRequest) =>
    http.post<Guest>('/guests', data).then((r) => r.data),

  update: (id: string, data: GuestUpdateRequest) =>
    http.patch<Guest>(`/guests/${id}`, data).then((r) => r.data),

  delete: (id: string) =>
    http.delete(`/guests/${id}`).then((r) => r.data),

  bulkImport: (guests: GuestCreateRequest[]) =>
    http.post<{ imported: number }>('/guests/import', { guests }).then((r) => r.data),
}
