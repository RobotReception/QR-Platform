import http from '@services/http/client'
import type {
  Team,
  TeamMember,
  CreateTeamRequest,
  UpdateTeamRequest,
  AddTeamMemberRequest,
  UpdateTeamMemberRequest,
} from '../types'

export const teamsAPI = {
  // ── Read ──
  list: async (): Promise<Team[]> => {
    const { data } = await http.get<Team[]>('/teams')
    return data
  },

  getById: async (teamId: string): Promise<Team> => {
    const { data } = await http.get<Team>(`/teams/${teamId}`)
    return data
  },

  // ── Create ──
  create: async (payload: CreateTeamRequest): Promise<Team> => {
    const { data } = await http.post<Team>('/teams', payload)
    return data
  },

  // ── Update ──
  update: async (teamId: string, payload: UpdateTeamRequest): Promise<Team> => {
    const { data } = await http.patch<Team>(`/teams/${teamId}`, payload)
    return data
  },

  // ── Delete ──
  remove: async (teamId: string): Promise<void> => {
    await http.delete(`/teams/${teamId}`)
  },

  // ── Archive/Activate ──
  archive: async (teamId: string): Promise<Team> => {
    return teamsAPI.update(teamId, { is_active: false })
  },

  activate: async (teamId: string): Promise<Team> => {
    return teamsAPI.update(teamId, { is_active: true })
  },

  // ══════════════════════════════════════════════
  // TEAM MEMBERS
  // ══════════════════════════════════════════════

  // ── Read ──
  members: async (teamId: string): Promise<TeamMember[]> => {
    const { data } = await http.get<TeamMember[]>(`/teams/${teamId}/members`)
    return data
  },

  // ── Add ──
  addMember: async (teamId: string, body: AddTeamMemberRequest): Promise<TeamMember> => {
    const { data } = await http.post<TeamMember>(`/teams/${teamId}/members`, body)
    return data
  },

  // ── Update ──
  updateMember: async (
    teamId: string,
    userId: string,
    body: UpdateTeamMemberRequest,
  ): Promise<TeamMember> => {
    // Backend uses upsert via POST
    const { data } = await http.post<TeamMember>(`/teams/${teamId}/members`, {
      user_id: userId,
      role: body.role,
    })
    return data
  },

  // ── Remove ──
  removeMember: async (teamId: string, userId: string): Promise<void> => {
    await http.delete(`/teams/${teamId}/members/${userId}`)
  },

  // ── Bulk Add ──
  addMembersBulk: async (
    teamId: string,
    members: AddTeamMemberRequest[],
  ): Promise<TeamMember[]> => {
    const results = await Promise.all(
      members.map((m) => teamsAPI.addMember(teamId, m)),
    )
    return results
  },
}
