import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { STORAGE } from '@services/http/client'
import type { AuthUser, TenantInfo } from '../types'

interface AuthStore {
  user:            AuthUser | null
  tenants:         TenantInfo[]
  currentTenantId: string | null
  permissions:     Set<string>
  isAuthenticated: boolean

  setAuth: (user: AuthUser, tenants: TenantInfo[], tenantId?: string, permissions?: string[]) => void
  setTenant: (tenantId: string) => void
  setPermissions: (permissions: string[]) => void
  clearAuth: () => void
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set) => ({
      user:            null,
      tenants:         [],
      currentTenantId: null,
      permissions:     new Set<string>(),
      isAuthenticated: false,

      setAuth: (user, tenants, tenantId, permissions) => {
        const tid = tenantId || tenants[0]?.tenant_id || null
        if (tid) localStorage.setItem(STORAGE.TENANT_ID, tid)
        set({
          user,
          tenants,
          currentTenantId: tid,
          permissions: new Set(permissions || []),
          isAuthenticated: true,
        })
      },

      setTenant: (tenantId) => {
        localStorage.setItem(STORAGE.TENANT_ID, tenantId)
        set({ currentTenantId: tenantId })
      },

      setPermissions: (permissions) => {
        set({ permissions: new Set(permissions) })
      },

      clearAuth: () => {
        Object.values(STORAGE).forEach(k => localStorage.removeItem(k))
        set({ user: null, tenants: [], currentTenantId: null, permissions: new Set(), isAuthenticated: false })
      },
    }),
    {
      name: 'qentry-auth',
      partialize: (s) => ({
        user:            s.user,
        tenants:         s.tenants,
        currentTenantId: s.currentTenantId,
        permissions:     Array.from(s.permissions),
        isAuthenticated: s.isAuthenticated,
      }),
      merge: (persisted, current) => {
        const p = persisted as Partial<AuthStore> & { permissions?: string[] }
        return {
          ...current,
          ...p,
          permissions: new Set(p.permissions || []),
        }
      },
    }
  )
)
