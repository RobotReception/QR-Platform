import { Users, Sparkles, UserCheck, Clock } from 'lucide-react'
import type { LiveStats } from '../api/checkinApi'

interface Props {
  stats: LiveStats | null | undefined
  isLoading: boolean
}

export function LiveStatsPanel({ stats, isLoading }: Props) {
  const s = stats?.stats

  if (isLoading || !s) {
    return (
      <div className="checkin-stats-grid">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="checkin-stat-card checkin-stat-card--skeleton">
            <div className="skeleton-line" style={{ width: '60%' }} />
            <div className="skeleton-line skeleton-line--lg" />
          </div>
        ))}
      </div>
    )
  }

  const cards = [
    {
      label: 'إجمالي الحضور',
      value: s.checked_in,
      total: s.total_valid,
      icon: UserCheck,
      color: '#10b981',
      pct: s.total_valid > 0 ? Math.round((s.checked_in / s.total_valid) * 100) : 0,
    },
    {
      label: 'VIP',
      value: s.vip_checked_in,
      total: s.total_vip,
      icon: Sparkles,
      color: '#C9A96E',
      pct: s.total_vip > 0 ? Math.round((s.vip_checked_in / s.total_vip) * 100) : 0,
    },
    {
      label: 'عادي',
      value: s.normal_checked_in,
      total: s.total_normal,
      icon: Users,
      color: '#3b82f6',
      pct: s.total_normal > 0 ? Math.round((s.normal_checked_in / s.total_normal) * 100) : 0,
    },
    {
      label: 'إجمالي الدعوات',
      value: s.total_valid,
      total: null,
      icon: Users,
      color: '#8b5cf6',
      pct: null,
    },
  ]

  return (
    <div className="checkin-stats-section">
      <div className="checkin-stats-grid">
        {cards.map((card) => (
          <div key={card.label} className="checkin-stat-card">
            <div className="checkin-stat-card__header">
              <card.icon size={16} style={{ color: card.color }} />
              <span>{card.label}</span>
            </div>
            <div className="checkin-stat-card__value" style={{ color: card.color }}>
              {card.value}
              {card.total !== null && (
                <span className="checkin-stat-card__total">/ {card.total}</span>
              )}
            </div>
            {card.pct !== null && (
              <div className="checkin-stat-card__bar">
                <div
                  className="checkin-stat-card__bar-fill"
                  style={{ width: `${card.pct}%`, background: card.color }}
                />
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Recent Check-ins */}
      {stats?.recent_checkins && stats.recent_checkins.length > 0 && (
        <div className="checkin-recent">
          <h4><Clock size={14} /> آخر عمليات الحضور</h4>
          <div className="checkin-recent-list">
            {stats.recent_checkins.map((item, i) => (
              <div key={i} className="checkin-recent-item">
                <span className="checkin-recent-name">
                  {item.ticket_class === 'vip' && <Sparkles size={12} className="inv-vip-icon" />}
                  {item.guest_name || 'ضيف'}
                </span>
                <span className="checkin-recent-time">
                  {new Date(item.created_at).toLocaleTimeString('ar', { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
