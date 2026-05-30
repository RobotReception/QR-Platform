/**
 * eventsStore.ts
 * Zustand store for Events feature UI state only.
 * Server state lives in React Query — this is purely for UI.
 */
import { create } from 'zustand'
import type { EventStatus } from '../types'

interface EventsUIState {
  // List page filters
  searchQuery: string
  statusFilter: EventStatus | ''
  // Actions
  setSearchQuery: (q: string) => void
  setStatusFilter: (s: EventStatus | '') => void
  resetFilters: () => void
}

export const useEventsStore = create<EventsUIState>((set) => ({
  searchQuery: '',
  statusFilter: '',
  setSearchQuery: (searchQuery) => set({ searchQuery }),
  setStatusFilter: (statusFilter) => set({ statusFilter }),
  resetFilters: () => set({ searchQuery: '', statusFilter: '' }),
}))
