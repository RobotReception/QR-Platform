import axios from 'axios'

function resolveApiBaseUrl() {
  const configured = import.meta.env.VITE_API_URL || '/api/v1'

  if (typeof window === 'undefined') return configured

  try {
    const url = new URL(configured)
    const isLoopbackHost = ['localhost', '127.0.0.1', '0.0.0.0'].includes(url.hostname)
    const isBrowserLocal = ['localhost', '127.0.0.1', '0.0.0.0'].includes(window.location.hostname)

    if (isLoopbackHost && !isBrowserLocal) {
      return '/api/v1'
    }

    return configured
  } catch {
    return configured
  }
}

export const BASE_URL = resolveApiBaseUrl()

// ── Storage Keys ──
export const STORAGE = {
  ACCESS_TOKEN:  'qentry_access_token',
  REFRESH_TOKEN: 'qentry_refresh_token',
  TENANT_ID:     'qentry_tenant_id',
  USER:          'qentry_user',
  TENANTS:       'qentry_tenants',
} as const

// ── Axios Instance ──
export const http = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 120_000,
})

// ── Request Interceptor: attach token + tenant ──
http.interceptors.request.use((config) => {
  const token    = localStorage.getItem(STORAGE.ACCESS_TOKEN)
  const tenantId = localStorage.getItem(STORAGE.TENANT_ID)

  if (token)    config.headers.Authorization  = `Bearer ${token}`
  if (tenantId) config.headers['X-Tenant-ID'] = tenantId

  return config
})

// ── Response Interceptor: auto refresh on 401 ──
http.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config as typeof error.config & { _retry?: boolean }

    const isAuthRoute = original?.url?.includes('/auth/login') ||
                        original?.url?.includes('/auth/refresh')

    if (error.response?.status === 401 && !original._retry && !isAuthRoute) {
      original._retry = true
      try {
        const refreshToken = localStorage.getItem(STORAGE.REFRESH_TOKEN)
        if (!refreshToken) throw new Error('no refresh token')

        const { data } = await axios.post(`${BASE_URL}/auth/refresh`, {
          refresh_token: refreshToken,
        }, { headers: { 'Content-Type': 'application/json' } })

        localStorage.setItem(STORAGE.ACCESS_TOKEN, data.access_token)
        if (data.refresh_token) {
          localStorage.setItem(STORAGE.REFRESH_TOKEN, data.refresh_token)
        }

        original.headers.Authorization = `Bearer ${data.access_token}`
        return http(original)
      } catch {
        // Clear storage and redirect to login
        Object.values(STORAGE).forEach(k => localStorage.removeItem(k))
        window.location.href = '/auth/login'
      }
    }

    return Promise.reject(error)
  }
)

export default http
