import http from '@services/http/client'

export interface PlanLimit {
  id: string
  plan_id: string
  key: string
  value: number
  period: string
}

export interface Plan {
  id: string
  code: string
  name: string
  description: string
  subtitle: string
  price_monthly: number
  price_yearly: number
  currency: string
  is_active: boolean
  sort_order: number
  badge_color: string
  is_popular: boolean
  is_customizable: boolean
  features: string[]
  limits: PlanLimit[]
}

export interface TenantSubscription {
  id: string
  tenant_id: string
  plan_id: string
  provider: string
  provider_customer_id: string | null
  provider_subscription_id: string | null
  status: string
  cancel_at_period_end: boolean
  current_period_start: string
  current_period_end: string
  created_at: string
  updated_at: string
  plan_code: string
  plan_name: string
}

export const subscriptionsAPI = {
  listPlans: async (): Promise<Plan[]> => {
    const { data } = await http.get<Plan[]>('/plans')
    return data
  },

  getCurrentSubscription: async (): Promise<TenantSubscription> => {
    const { data } = await http.get<TenantSubscription>('/subscriptions/current')
    return data
  },

  createCheckoutSession: async (planCode: string, paymentProvider: string = 'paypal'): Promise<{ checkout_url: string; session_id: string; token?: string }> => {
    const { data } = await http.post<{ checkout_url: string; session_id: string; token?: string }>(
      `/subscriptions/checkout?plan_code=${planCode}&payment_provider=${paymentProvider}`
    )
    return data
  },

  executePayPalSubscription: async (token: string): Promise<{ message: string; subscription_id: string }> => {
    const { data } = await http.post<{ message: string; subscription_id: string }>(
      `/subscriptions/paypal/execute?token=${token}`
    )
    return data
  },

  cancelSubscription: async (): Promise<{ message: string }> => {
    const { data } = await http.post<{ message: string }>('/subscriptions/cancel')
    return data
  },
}
