import { useEffect, useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { Loader2, CheckCircle, XCircle } from 'lucide-react'
import { subscriptionsAPI } from '../api/subscriptionsApi'
import { useAuthStore } from '@features/auth/store/authStore'

export default function PayPalExecutePage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const currentTenantId = useAuthStore(s => s.currentTenantId)
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [message, setMessage] = useState('جاري تنفيذ الاشتراك...')

  useEffect(() => {
    const token = searchParams.get('token')
    
    if (!token) {
      setStatus('error')
      setMessage('لم يتم العثور على رمز الموافقة')
      return
    }

    // Execute PayPal subscription
    subscriptionsAPI.executePayPalSubscription(token)
      .then((result) => {
        setStatus('success')
        setMessage('تم تفعيل اشتراكك بنجاح!')

        if (currentTenantId) {
          void queryClient.invalidateQueries({ queryKey: ['dashboard', currentTenantId] })
          void queryClient.invalidateQueries({ queryKey: ['settings-usage', currentTenantId] })
          void queryClient.invalidateQueries({ queryKey: ['settings-tenant', currentTenantId] })
          void queryClient.invalidateQueries({ queryKey: ['current-subscription', currentTenantId] })
        }
        
        // Redirect to dashboard after 2 seconds
        setTimeout(() => {
          const params = new URLSearchParams({ upgrade_success: 'true' })
          if (result.plan_code) params.set('plan', result.plan_code)
          navigate(`/dashboard?${params.toString()}`, { replace: true })
        }, 2000)
      })
      .catch((error) => {
        setStatus('error')
        setMessage('فشل تنفيذ الاشتراك. يرجى المحاولة مرة أخرى أو التواصل مع الدعم.')
        console.error('PayPal execution error:', error)
      })
  }, [searchParams, navigate, currentTenantId, queryClient])

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '100vh',
      padding: '20px',
      background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
    }}>
      <div style={{
        background: 'rgba(255, 255, 255, 0.05)',
        backdropFilter: 'blur(10px)',
        borderRadius: '20px',
        padding: '40px',
        maxWidth: '400px',
        width: '100%',
        textAlign: 'center',
        border: '1px solid rgba(255, 255, 255, 0.1)',
      }}>
        {status === 'loading' && (
          <>
            <Loader2 size={48} className="spin" style={{ color: '#c9a96e', marginBottom: '20px' }} />
            <h2 style={{ color: '#fff', marginBottom: '10px', fontSize: '20px' }}>جاري تنفيذ الاشتراك</h2>
            <p style={{ color: '#94a3b8', fontSize: '14px' }}>{message}</p>
          </>
        )}

        {status === 'success' && (
          <>
            <CheckCircle size={48} style={{ color: '#10b981', marginBottom: '20px' }} />
            <h2 style={{ color: '#fff', marginBottom: '10px', fontSize: '20px' }}>تم بنجاح!</h2>
            <p style={{ color: '#94a3b8', fontSize: '14px' }}>{message}</p>
            <p style={{ color: '#64748b', fontSize: '12px', marginTop: '20px' }}>سيتم توجيهك إلى لوحة التحكم...</p>
          </>
        )}

        {status === 'error' && (
          <>
            <XCircle size={48} style={{ color: '#ef4444', marginBottom: '20px' }} />
            <h2 style={{ color: '#fff', marginBottom: '10px', fontSize: '20px' }}>حدث خطأ</h2>
            <p style={{ color: '#94a3b8', fontSize: '14px', marginBottom: '20px' }}>{message}</p>
            <button
              onClick={() => navigate('/dashboard')}
              style={{
                background: '#c9a96e',
                color: '#1a1a2e',
                border: 'none',
                padding: '12px 24px',
                borderRadius: '8px',
                fontSize: '14px',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 0.2s',
              }}
              onMouseOver={(e) => e.currentTarget.style.opacity = '0.9'}
              onMouseOut={(e) => e.currentTarget.style.opacity = '1'}
            >
              العودة إلى لوحة التحكم
            </button>
          </>
        )}
      </div>
    </div>
  )
}
