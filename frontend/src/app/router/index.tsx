import { lazy, Suspense, useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from '@features/auth/store/authStore'

const LoginPage          = lazy(() => import('@features/auth/pages/LoginPage'))
const SignupPage         = lazy(() => import('@features/auth/pages/SignupPage'))
const ForgotPasswordPage = lazy(() => import('@features/auth/pages/ForgotPasswordPage'))
const DashboardPage      = lazy(() => import('@features/dashboard/pages/DashboardPage'))
const UsersPage          = lazy(() => import('@features/users/pages/UsersPage'))
const TeamsPage          = lazy(() => import('@features/teams/pages/TeamsPage'))
const EventsPage         = lazy(() => import('@features/events/pages/EventsPage'))
const EventDetailsPage   = lazy(() => import('@features/events/pages/EventDetailsPage'))
const EventDesignEditorPage = lazy(() => import('@features/events/pages/EventDesignEditorPage'))
const PublicInvitationPage = lazy(() => import('@features/invitations/pages/PublicInvitationPage'))
const PublicRegistrationPage = lazy(() => import('@features/invitations/pages/PublicRegistrationPage'))
const PlatformAdminPage  = lazy(() => import('@features/platform/pages/PlatformAdminPage'))
const SettingsPage       = lazy(() => import('@features/settings/pages/SettingsPage'))
const PayPalExecutePage  = lazy(() => import('@features/settings/pages/PayPalExecutePage'))

function LoadingScreen() {
  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: '#0F172A',
    }}>
      <div style={{
        width: 40,
        height: 40,
        border: '3px solid rgba(201,169,110,0.2)',
        borderTopColor: '#C9A96E',
        borderRadius: '50%',
        animation: 'spin 0.8s linear infinite',
      }} />
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  )
}

function useAuthHydrated() {
  const [hydrated, setHydrated] = useState(() => useAuthStore.persist.hasHydrated())

  useEffect(() => {
    if (useAuthStore.persist.hasHydrated()) {
      setHydrated(true)
      return
    }

    const unsubscribe = useAuthStore.persist.onFinishHydration(() => {
      setHydrated(true)
    })

    return unsubscribe
  }, [])

  return hydrated
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore(s => s.isAuthenticated)
  const hasHydrated = useAuthHydrated()

  if (!hasHydrated) {
    return <LoadingScreen />
  }

  return isAuthenticated ? <>{children}</> : <Navigate to="/auth/login" replace />
}

function StaffRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore(s => s.isAuthenticated)
  const user = useAuthStore(s => s.user)
  const hasHydrated = useAuthHydrated()

  if (!hasHydrated) return <LoadingScreen />
  if (!isAuthenticated) return <Navigate to="/auth/login" replace />
  if (!user?.is_staff) return <Navigate to="/dashboard" replace />

  return <>{children}</>
}

function RootRedirect() {
  const isAuthenticated = useAuthStore(s => s.isAuthenticated)
  const hasHydrated = useAuthHydrated()

  if (!hasHydrated) {
    return <LoadingScreen />
  }

  return <Navigate to={isAuthenticated ? '/dashboard' : '/auth/login'} replace />
}

export default function AppRouter() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Suspense fallback={<LoadingScreen />}>
        <Routes>
          {/* ── Auth Routes ── */}
          <Route path="/auth/login"          element={<LoginPage />} />
          <Route path="/auth/signup"         element={<SignupPage />} />
          <Route path="/auth/forgot-password" element={<ForgotPasswordPage />} />

          {/* ── Public Routes (no auth) ── */}
          <Route path="/i/:token" element={<PublicInvitationPage />} />
          <Route path="/register/:slug" element={<PublicRegistrationPage />} />
          <Route path="/e/:slug" element={<PublicRegistrationPage />} />

          {/* ── Protected Routes ── */}
          <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
          <Route path="/users"     element={<ProtectedRoute><UsersPage /></ProtectedRoute>} />
          <Route path="/teams"     element={<ProtectedRoute><TeamsPage /></ProtectedRoute>} />
          <Route path="/guests" element={<Navigate to="/events" replace />} />
          <Route path="/invitations" element={<Navigate to="/events" replace />} />
          <Route path="/checkin" element={<Navigate to="/events" replace />} />
          <Route path="/settings"  element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
          <Route path="/settings/roles" element={<Navigate to="/platform" replace />} />
          <Route path="/billing/paypal/execute" element={<ProtectedRoute><PayPalExecutePage /></ProtectedRoute>} />

          <Route path="/events"    element={<ProtectedRoute><EventsPage /></ProtectedRoute>} />
          <Route path="/events/:eventId" element={<ProtectedRoute><EventDetailsPage /></ProtectedRoute>} />
          <Route path="/events/:eventId/design" element={<ProtectedRoute><EventDesignEditorPage /></ProtectedRoute>} />

          {/* ── Platform Admin (Staff Only) ── */}
          <Route path="/platform" element={<StaffRoute><PlatformAdminPage /></StaffRoute>} />

          {/* ── Fallbacks ── */}
          <Route path="/"  element={<RootRedirect />} />
          <Route path="*"  element={<RootRedirect />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}

