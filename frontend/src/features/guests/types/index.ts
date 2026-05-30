/* ── Guest Types ── */

export interface Guest {
  id: string
  tenant_id: string
  full_name: string
  full_name_ar: string | null
  phone: string | null
  email: string | null
  company: string | null
  title: string | null
  custom_fields: Record<string, any> | null
  notes: string | null
  created_at: string
  updated_at: string
}

export interface GuestCreateRequest {
  full_name: string
  full_name_ar?: string
  phone?: string
  email?: string
  company?: string
  title?: string
  custom_fields?: Record<string, any>
  notes?: string
}

export interface GuestUpdateRequest {
  full_name?: string
  full_name_ar?: string
  phone?: string
  email?: string
  company?: string
  title?: string
  custom_fields?: Record<string, any>
  notes?: string
}
