/**
 * Public API for the Events feature.
 * Import from '@features/events' instead of deep paths.
 */

// Pages
export { default as EventsPage } from './pages/EventsPage'
export { default as EventDetailsPage } from './pages/EventDetailsPage'

// Components
export { EventCard } from './components/EventCard'
export { EventSkeletonCard, EventSkeletonGrid } from './components/EventSkeletonCard'
export { EventStatsStrip } from './components/EventStatsStrip'
export { EventSettingsForm } from './components/EventSettingsForm'
export { EventGatesTab } from './components/EventGatesTab'
export { ConfirmDialog } from './components/ConfirmDialog'
export { CreateEventDialog } from './components/CreateEventDialog'
export { CreateGateDialog } from './components/CreateGateDialog'

// Hooks
export { useEventsList, useEventCreate, useEventDelete } from './hooks/useEvents'
export {
  useEventDetail,
  useEventStats,
  useEventGates,
  useEventUpdate,
  useEventPublish,
  useGateCreate,
  useGateDelete,
} from './hooks/useEventDetails'

// Store
export { useEventsStore } from './store/eventsStore'

// API + Keys
export { eventsAPI, eventKeys } from './api/eventsApi'

// Utils
export {
  STATUS_LABELS,
  STATUS_CSS,
  getStatusConfig,
  formatDateFull,
  formatDateShort,
  calcOccupancy,
  STATUS_TRANSITIONS,
  canTransition,
} from './utils/eventUtils'

// Types
export type {
  EventModel,
  EventStatus,
  EventCategory,
  EventType,
  EventGate,
  EventGateCreate,
  EventStats,
  EventCreateRequest,
  EventUpdateRequest,
  EventStatusTransitionRequest,
  EventAsset,
  EventAssetCreate,
  TicketClass,
} from './types'
