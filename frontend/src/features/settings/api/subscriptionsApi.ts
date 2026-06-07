import http from '@services/http/client'

export type BillingPeriod = 'monthly' | 'yearly'

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
  price_monthly: number | null
  price_yearly: number | null
  currency: string | null
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

  createCheckoutSession: async (
    planCode: string,
    billingPeriod: BillingPeriod = 'monthly',
    paymentProvider: string = 'paypal',
  ): Promise<{ checkout_url: string; session_id: string; token?: string }> => {
    const params = new URLSearchParams({
      plan_code: planCode,
      payment_provider: paymentProvider,
      billing_period: billingPeriod,
    })
    const { data } = await http.post<{ checkout_url: string; session_id: string; token?: string }>(
      `/subscriptions/checkout?${params.toString()}`
    )
    return data
  },

  executePayPalSubscription: async (token: string): Promise<{ message: string; subscription_id: string; plan_code?: string; billing_period?: BillingPeriod }> => {
    const params = new URLSearchParams({ token })
    const { data } = await http.post<{ message: string; subscription_id: string; plan_code?: string; billing_period?: BillingPeriod }>(
      `/subscriptions/paypal/execute?${params.toString()}`
    )
    return data
  },

  changePlan: async (planCode: string): Promise<{ message: string; plan_code: string }> => {
    const params = new URLSearchParams({ plan_code: planCode })
    const { data } = await http.post<{ message: string; plan_code: string }>(
      `/subscriptions/change-plan?${params.toString()}`
    )
    return data
  },

  cancelSubscription: async (): Promise<{ message: string }> => {
    const { data } = await http.post<{ message: string }>('/subscriptions/cancel')
    return data
  },
}
