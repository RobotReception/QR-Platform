import { useMutation, useQueryClient } from '@tanstack/react-query'
import { invitationsApi, FastInvitationRequest, FastGenerationResponse } from '../api/invitationsApi'
import { useAuthStore } from '@features/auth/store/authStore'

export const useGenerateInvitations = () => {
  const queryClient = useQueryClient()
  const tenantId = useAuthStore((s) => s.currentTenantId)

  return useMutation<FastGenerationResponse, Error, FastInvitationRequest>({
    mutationFn: (data) => invitationsApi.generateFast(data),
    onSuccess: (_res, variables) => {
      // Invalidate relevant event queries
      queryClient.invalidateQueries({
        queryKey: ['event-stats', variables.event_id],
      })
      queryClient.invalidateQueries({
        queryKey: ['events', tenantId, 'detail', variables.event_id],
      })
      queryClient.invalidateQueries({
        queryKey: ['fast-generation-history', variables.event_id],
      })
      queryClient.invalidateQueries({
        queryKey: ['invitations'],
      })
    },
  })
}
