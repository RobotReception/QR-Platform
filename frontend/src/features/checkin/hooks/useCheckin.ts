/**
 * useCheckin.ts
 * React Query hooks for check-in operations.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { checkinAPI, checkinKeys, type CheckinRequest } from '../api/checkinApi'

export function useScanCheckin() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: CheckinRequest) => checkinAPI.scan(data),
    onSuccess: () => {
      // Invalidate live stats for all events
      qc.invalidateQueries({ queryKey: ['checkin'] })
    },
  })
}

export function useCheckinHistory(eventId?: string) {
  return useQuery({
    queryKey: checkinKeys.history(eventId || ''),
    queryFn: () => checkinAPI.history(eventId),
    enabled: !!eventId,
  })
}

export function useLiveStats(eventId: string) {
  return useQuery({
    queryKey: checkinKeys.live(eventId),
    queryFn: () => checkinAPI.liveStats(eventId),
    enabled: !!eventId,
    refetchInterval: 5000, // Auto-refresh every 5s
  })
}
