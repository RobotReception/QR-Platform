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
const InvitationsPage    = lazy(() => import('@features/invitations/pages/InvitationsPage'))
const PublicInvitationPage = lazy(() => import('@features/invitations/pages/PublicInvitationPage'))
const GuestsPage         = lazy(() => import('@features/guests/pages/GuestsPage'))
const CheckinPage        = lazy(() => import('@features/checkin/pages/CheckinPage'))

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
    <BrowserRouter>
      <Suspense fallback={<LoadingScreen />}>
        <Routes>
          {/* ── Auth Routes ── */}
          <Route path="/auth/login"          element={<LoginPage />} />
          <Route path="/auth/signup"         element={<SignupPage />} />
          <Route path="/auth/forgot-password" element={<ForgotPasswordPage />} />

          {/* ── Public Routes (no auth) ── */}
          <Route path="/i/:token" element={<PublicInvitationPage />} />

          {/* ── Protected Routes ── */}
          <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
          <Route path="/users"     element={<ProtectedRoute><UsersPage /></ProtectedRoute>} />
          <Route path="/teams"     element={<ProtectedRoute><TeamsPage /></ProtectedRoute>} />

          <Route path="/events"    element={<ProtectedRoute><EventsPage /></ProtectedRoute>} />
          <Route path="/events/:eventId" element={<ProtectedRoute><EventDetailsPage /></ProtectedRoute>} />
          <Route path="/events/:eventId/design" element={<ProtectedRoute><EventDesignEditorPage /></ProtectedRoute>} />

          <Route path="/invitations" element={<ProtectedRoute><InvitationsPage /></ProtectedRoute>} />
          <Route path="/guests"      element={<ProtectedRoute><GuestsPage /></ProtectedRoute>} />
          <Route path="/checkin"     element={<ProtectedRoute><CheckinPage /></ProtectedRoute>} />

          {/* ── Fallbacks ── */}
          <Route path="/"  element={<RootRedirect />} />
          <Route path="*"  element={<RootRedirect />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}
