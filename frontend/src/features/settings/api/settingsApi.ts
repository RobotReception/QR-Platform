import http from '@services/http/client'

export interface TenantDetails {
  id: string
  slug: string
  name: string
  status: string
  plan: string
  created_at: string
  updated_at: string
}

export interface UsageLimit {
  key: string
  limit: number
  current_usage: number
  remaining: number
  is_exceeded: boolean
}

export interface UsageSummary {
  tenant_id: string
  plan_code: string
  limits: UsageLimit[]
  any_exceeded: boolean
}

export const settingsAPI = {
  getCurrentTenant: async (): Promise<TenantDetails> => {
    const { data } = await http.get<TenantDetails>('/tenants/current')
    return data
  },

  updateTenant: async (body: { name?: string; slug?: string }): Promise<TenantDetails> => {
    const { data } = await http.patch<TenantDetails>('/tenants/current', body)
    return data
  },

  getUsage: async (): Promise<UsageSummary> => {
    const { data } = await http.get<UsageSummary>('/usage')
    return data
  },
}
