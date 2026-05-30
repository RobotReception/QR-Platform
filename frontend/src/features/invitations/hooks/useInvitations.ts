/**
 * useInvitations.ts
 * React Query hooks for invitations CRUD operations.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuthStore } from '@features/auth/store/authStore'
import { invitationsAPI, invitationKeys } from '../api/invitationsApi'
import type {
  InvitationCreateRequest,
  QuickInviteRequest,
  BulkFromGuestsRequest,
  InvitationUpdateRequest,
  InvitationSendRequest,
  InvitationListParams,
} from '../types'

export function useInvitationsList(params?: InvitationListParams) {
  const tenantId = useAuthStore((s) => s.currentTenantId) ?? ''
  return useQuery({
    queryKey: invitationKeys.list(tenantId, params),
    queryFn: () => invitationsAPI.list(params),
    enabled: !!tenantId,
  })
}

export function useInvitationDetail(id: string) {
  const tenantId = useAuthStore((s) => s.currentTenantId) ?? ''
  return useQuery({
    queryKey: invitationKeys.detail(tenantId, id),
    queryFn: () => invitationsAPI.get(id),
    enabled: !!tenantId && !!id,
  })
}

export function useCreateInvitation() {
  const qc = useQueryClient()
  const tenantId = useAuthStore((s) => s.currentTenantId) ?? ''
  return useMutation({
    mutationFn: (data: InvitationCreateRequest) => invitationsAPI.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: invitationKeys.all(tenantId) }),
  })
}

export function useQuickInvitations() {
  const qc = useQueryClient()
  const tenantId = useAuthStore((s) => s.currentTenantId) ?? ''
  return useMutation({
    mutationFn: (data: QuickInviteRequest) => invitationsAPI.quickCreate(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: invitationKeys.all(tenantId) }),
  })
}

export function useBulkFromGuests() {
  const qc = useQueryClient()
  const tenantId = useAuthStore((s) => s.currentTenantId) ?? ''
  return useMutation({
    mutationFn: (data: BulkFromGuestsRequest) => invitationsAPI.bulkFromGuests(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: invitationKeys.all(tenantId) }),
  })
}

export function useUpdateInvitation() {
  const qc = useQueryClient()
  const tenantId = useAuthStore((s) => s.currentTenantId) ?? ''
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: InvitationUpdateRequest }) =>
      invitationsAPI.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: invitationKeys.all(tenantId) }),
  })
}

export function useRevokeInvitation() {
  const qc = useQueryClient()
  const tenantId = useAuthStore((s) => s.currentTenantId) ?? ''
  return useMutation({
    mutationFn: (id: string) => invitationsAPI.revoke(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: invitationKeys.all(tenantId) }),
  })
}

export function useSendInvitations() {
  const qc = useQueryClient()
  const tenantId = useAuthStore((s) => s.currentTenantId) ?? ''
  return useMutation({
    mutationFn: (data: InvitationSendRequest) => invitationsAPI.send(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: invitationKeys.all(tenantId) }),
  })
}
