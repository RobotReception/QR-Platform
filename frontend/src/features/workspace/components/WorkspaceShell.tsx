import type { ReactNode } from 'react'
import { NavLink } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import {
  CalendarDays, LayoutDashboard, Settings, Users, UserRoundCog,
  Shield, LogOut, Building2, ChevronDown,
} from 'lucide-react'
import { useAuthStore } from '@features/auth/store/authStore'
import { usePermission } from '@shared/permissions'
import { PERM } from '@shared/permissions'
import { useLoadPermissions } from '@features/permissions/hooks/useLoadPermissions'
import '@features/dashboard/pages/dashboard.css'

function NavItem({ to, icon: Icon, label }: { to: string; icon: typeof LayoutDashboard; label: string }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) => `dash-nav__item${isActive ? ' dash-nav__item--active' : ''}`}
      aria-current={undefined}
    >
      <Icon size={18} />{label}
    </NavLink>
  )
}

function PermNavItem({ permission, to, icon, label }: {
  permission: string
  to: string
  icon: typeof LayoutDashboard
  label: string
}) {
  const allowed = usePermission(permission)
  if (!allowed) return null
  return <NavItem to={to} icon={icon} label={label} />
}

export function WorkspaceShell({
  title,
  subtitle,
  actions,
  children,
  hideSidebar = false,
}: {
  title: string
  subtitle: string
  actions?: ReactNode
  children: ReactNode
  hideSidebar?: boolean
}) {
  const user = useAuthStore(s => s.user)
  const tenants = useAuthStore(s => s.tenants)
  const currentTenantId = useAuthStore(s => s.currentTenantId)
  const setTenant = useAuthStore(s => s.setTenant)
  const clearAuth = useAuthStore(s => s.clearAuth)
  const queryClient = useQueryClient()

  useLoadPermissions()

  const currentTenant = tenants.find(t => t.tenant_id === currentTenantId)

  const handleTenantChange = (tenantId: string) => {
    if (tenantId === currentTenantId) return
    setTenant(tenantId)
    queryClient.invalidateQueries()
  }

  return (
    <div className={`dashboard-shell${hideSidebar ? ' dashboard-shell--full' : ''}`}>
      {!hideSidebar ? <aside className="dash-sidebar">
        <div className="dash-brand">
          <img src="/logo.png" alt="Qentry" />
          <div>
            <strong>Qentry</strong>
            <span>Event OS</span>
          </div>
        </div>

        {tenants.length > 0 && (
          <div className="dash-tenant-switcher">
            <label className="dash-tenant-switcher__label" htmlFor="tenant-select">
              <Building2 size={14} />
              المؤسسة
            </label>
            {tenants.length === 1 ? (
              <div className="dash-tenant-switcher__single">{currentTenant?.name || '—'}</div>
            ) : (
              <div className="dash-tenant-switcher__select-wrap">
                <select
                  id="tenant-select"
                  className="dash-tenant-switcher__select"
                  value={currentTenantId || ''}
                  onChange={(e) => handleTenantChange(e.target.value)}
                >
                  {tenants.map(t => (
                    <option key={t.tenant_id} value={t.tenant_id}>{t.name}</option>
                  ))}
                </select>
                <ChevronDown size={14} className="dash-tenant-switcher__icon" />
              </div>
            )}
          </div>
        )}

        <nav className="dash-nav" aria-label="Workspace Navigation">
          <PermNavItem permission={PERM.NAV_DASHBOARD} to="/dashboard" icon={LayoutDashboard} label="الرئيسية" />
          <PermNavItem permission={PERM.NAV_USERS} to="/users" icon={UserRoundCog} label="المستخدمون" />
          <PermNavItem permission={PERM.NAV_TEAMS} to="/teams" icon={Users} label="الفرق" />
          <PermNavItem permission={PERM.NAV_EVENTS} to="/events" icon={CalendarDays} label="الأحداث" />
          <PermNavItem permission={PERM.NAV_SETTINGS} to="/settings" icon={Settings} label="الإعدادات" />
          {user?.is_staff && (
            <>
              <div style={{ borderTop: '1px solid rgba(255,255,255,0.06)', margin: '12px 0' }} />
              <NavItem to="/platform" icon={Shield} label="إدارة المنصة" />
            </>
          )}
        </nav>

        <div className="dash-sidebar__footer">
          <button className="dash-nav__item dash-nav__item--danger" onClick={clearAuth}>
            <LogOut size={18} />
            <span>تسجيل الخروج</span>
          </button>
        </div>
      </aside> : null}

      <main className="dash-main">
        <header className="dash-header">
          <div>
            <span className="dash-kicker">لوحة التشغيل</span>
            <h1>{title}</h1>
            <p>{subtitle}</p>
          </div>
          {actions ? <div className="dash-header__actions">{actions}</div> : null}
        </header>

        {children}
      </main>
    </div>
  )
}
