import type { ReactNode } from 'react'
import { NavLink } from 'react-router-dom'
import { CalendarDays, LayoutDashboard, QrCode, Settings, Ticket, Users, UserRoundCog, BookUser } from 'lucide-react'
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

        <nav className="dash-nav" aria-label="Workspace Navigation">
          <NavItem to="/dashboard" icon={LayoutDashboard} label="الرئيسية" />
          <NavItem to="/users" icon={UserRoundCog} label="المستخدمون" />
          <NavItem to="/teams" icon={Users} label="الفرق" />
          <NavItem to="/events" icon={CalendarDays} label="الأحداث" />
          <NavItem to="/guests" icon={BookUser} label="الضيوف" />
          <NavItem to="/invitations" icon={Ticket} label="الدعوات" />
          <NavItem to="/checkin" icon={QrCode} label="الحضور" />
          <NavItem to="/settings" icon={Settings} label="الإعدادات" />
        </nav>
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
