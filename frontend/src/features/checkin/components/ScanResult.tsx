import type { CheckinResponse } from '../api/checkinApi'
import { CheckCircle2, XCircle, AlertTriangle, Sparkles, User } from 'lucide-react'

interface Props {
  result: CheckinResponse | null
}

const RESULT_CONFIGS: Record<string, { icon: any; color: string; bg: string }> = {
  success: { icon: CheckCircle2, color: '#10b981', bg: 'rgba(16,185,129,0.08)' },
  already_checked_in: { icon: AlertTriangle, color: '#f59e0b', bg: 'rgba(245,158,11,0.08)' },
  revoked: { icon: XCircle, color: '#ef4444', bg: 'rgba(239,68,68,0.08)' },
  expired: { icon: XCircle, color: '#9ca3af', bg: 'rgba(156,163,175,0.08)' },
  invalid: { icon: XCircle, color: '#ef4444', bg: 'rgba(239,68,68,0.08)' },
  wrong_event: { icon: AlertTriangle, color: '#f59e0b', bg: 'rgba(245,158,11,0.08)' },
  wrong_gate: { icon: AlertTriangle, color: '#f59e0b', bg: 'rgba(245,158,11,0.08)' },
}

export function ScanResult({ result }: Props) {
  if (!result) return null

  const config = RESULT_CONFIGS[result.result] || RESULT_CONFIGS.invalid
  const Icon = config.icon
  const isVip = result.ticket_class === 'vip'

  return (
    <div
      className="scan-result"
      style={{ background: config.bg, borderColor: config.color + '30' }}
    >
      <div className="scan-result__icon" style={{ color: config.color }}>
        <Icon size={48} />
      </div>

      <div className="scan-result__message" style={{ color: config.color }}>
        {result.message}
      </div>

      {result.guest_name && (
        <div className="scan-result__guest">
          <User size={18} />
          <span>{result.guest_name}</span>
          {isVip && (
            <span className="scan-result__vip">
              <Sparkles size={14} /> VIP
            </span>
          )}
        </div>
      )}

      {result.event_title && (
        <div className="scan-result__event">{result.event_title}</div>
      )}

      {result.checkin_count !== undefined && (
        <div className="scan-result__count">
          مرات الدخول المسجلة: {result.checkin_count} / {result.guest_count || 1}
        </div>
      )}
    </div>
  )
}
