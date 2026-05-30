import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { STORAGE } from '@services/http/client'
import type { AuthUser, TenantInfo } from '../types'

interface AuthStore {
  user:            AuthUser | null
  tenants:         TenantInfo[]
  currentTenantId: string | null
  isAuthenticated: boolean

  setAuth: (user: AuthUser, tenants: TenantInfo[], tenantId?: string) => void
  setTenant: (tenantId: string) => void
  clearAuth: () => void
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set) => ({
      user:            null,
      tenants:         [],
      currentTenantId: null,
      isAuthenticated: false,

      setAuth: (user, tenants, tenantId) => {
        const tid = tenantId || tenants[0]?.tenant_id || null
        if (tid) localStorage.setItem(STORAGE.TENANT_ID, tid)
        set({ user, tenants, currentTenantId: tid, isAuthenticated: true })
      },

      setTenant: (tenantId) => {
        localStorage.setItem(STORAGE.TENANT_ID, tenantId)
        set({ currentTenantId: tenantId })
      },

      clearAuth: () => {
        Object.values(STORAGE).forEach(k => localStorage.removeItem(k))
        set({ user: null, tenants: [], currentTenantId: null, isAuthenticated: false })
      },
    }),
    {
      name: 'qentry-auth',
      partialize: (s) => ({
        user:            s.user,
        tenants:         s.tenants,
        currentTenantId: s.currentTenantId,
        isAuthenticated: s.isAuthenticated,
      }),
    }
  )
)
