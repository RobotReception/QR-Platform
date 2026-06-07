import http from '@services/http/client'

export interface RoleInfo {
  id: string
  tenant_id: string
  name: string
  description: string | null
  is_system_role: boolean
  created_at: string
  permissions: string[] | null
}

export interface PermissionInfo {
  key: string
  description: string | null
}

export const permissionsAPI = {
  getMyPermissions: async (): Promise<string[]> => {
    const { data } = await http.get<string[]>('/roles/me/permissions')
    return data
  },

  listRoles: async (): Promise<RoleInfo[]> => {
    const { data } = await http.get<RoleInfo[]>('/roles')
    return data
  },

  listAllPermissions: async (): Promise<PermissionInfo[]> => {
    const { data } = await http.get<PermissionInfo[]>('/roles/permissions')
    return data
  },

  updateRole: async (roleId: string, body: { permissions: string[] }): Promise<RoleInfo> => {
    const { data } = await http.patch<RoleInfo>(`/roles/${roleId}`, body)
    return data
  },

  createRole: async (body: { name: string; description?: string; permissions: string[] }): Promise<RoleInfo> => {
    const { data } = await http.post<RoleInfo>('/roles', body)
    return data
  },

  deleteRole: async (roleId: string): Promise<void> => {
    await http.delete(`/roles/${roleId}`)
  },

  assignRole: async (memberId: string, roleId: string): Promise<void> => {
    await http.post('/roles/assign', null, { params: { member_id: memberId, role_id: roleId } })
  },

  unassignRole: async (memberId: string, roleId: string): Promise<void> => {
    await http.post('/roles/unassign', null, { params: { member_id: memberId, role_id: roleId } })
  },
}
