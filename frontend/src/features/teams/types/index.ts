export interface Team {
  id: string
  tenant_id: string
  name: string
  description?: string | null
  color?: string | null
  is_active: boolean
  created_by?: string | null
  member_count?: number
  created_at: string
  updated_at: string
}

export interface TeamMember {
  id: string
  team_id: string
  user_id: string
  role: 'lead' | 'member' | 'viewer'
  joined_at: string
  full_name?: string | null
  avatar_url?: string | null
}

// ── API Requests ──
export interface CreateTeamRequest {
  name: string
  description?: string
  color?: string
}

export interface UpdateTeamRequest {
  name?: string
  description?: string
  color?: string
  is_active?: boolean
}

export interface AddTeamMemberRequest {
  user_id: string
  role: 'lead' | 'member' | 'viewer'
}

export interface UpdateTeamMemberRequest {
  role: 'lead' | 'member' | 'viewer'
}

// ── Filters ──
export interface TeamFilters {
  search?: string
  isActive?: boolean | 'all'
  hasMembers?: boolean | 'all'
}

// ── Stats ──
export interface TeamStats {
  totalTeams: number
  activeTeams: number
  archivedTeams: number
  totalMembers: number
  unassignedMembers: number
}
