/**
 * useGuests.ts
 * React Query hooks for guests CRUD.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuthStore } from '@features/auth/store/authStore'
import { guestsAPI, guestKeys } from '../api/guestsApi'
import type { GuestCreateRequest, GuestUpdateRequest } from '../types'

export function useGuestsList(search?: string) {
  const tenantId = useAuthStore((s) => s.currentTenantId) ?? ''
  return useQuery({
    queryKey: guestKeys.list(tenantId, search),
    queryFn: () => guestsAPI.list(search),
    enabled: !!tenantId,
  })
}

export function useCreateGuest() {
  const qc = useQueryClient()
  const tenantId = useAuthStore((s) => s.currentTenantId) ?? ''
  return useMutation({
    mutationFn: (data: GuestCreateRequest) => guestsAPI.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: guestKeys.all(tenantId) }),
  })
}

export function useUpdateGuest() {
  const qc = useQueryClient()
  const tenantId = useAuthStore((s) => s.currentTenantId) ?? ''
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: GuestUpdateRequest }) => guestsAPI.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: guestKeys.all(tenantId) }),
  })
}

export function useDeleteGuest() {
  const qc = useQueryClient()
  const tenantId = useAuthStore((s) => s.currentTenantId) ?? ''
  return useMutation({
    mutationFn: (id: string) => guestsAPI.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: guestKeys.all(tenantId) }),
  })
}
