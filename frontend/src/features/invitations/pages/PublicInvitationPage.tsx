/**
 * PublicInvitationPage.tsx
 * Public page shown to guests at /i/:token — no auth required.
 * Displays invitation details, event info, QR code, and RSVP buttons.
 */
import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import {
  CalendarDays, MapPin, Clock, CheckCircle2, XCircle,
  Sparkles, Loader2, ExternalLink,
} from 'lucide-react'
import { invitationsAPI } from '../api/invitationsApi'

interface PublicInvitation {
  id: string
  token: string
  status: string
  ticket_class: string
  guest_name: string | null
  guest_name_ar: string | null
  seat_number: string | null
  table_number: string | null
  hall: string | null
  zone: string | null
  barcode_png_url: string | null
  render_image_url: string | null
  card_image_url: string | null
  qr_data: string | null
  rsvp_status: string | null
  plus_one_count: number
  event_title: string | null
  event_title_ar: string | null
  start_date: string | null
  end_date: string | null
  venue_name: string | null
  venue_name_ar: string | null
  venue_address: string | null
  venue_map_url: string | null
  allow_rsvp: boolean
  allow_plus_one: boolean
  cover_image_url: string | null
}

export default function PublicInvitationPage() {
  const { token } = useParams<{ token: string }>()
  const [invitation, setInvitation] = useState<PublicInvitation | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [rsvpDone, setRsvpDone] = useState(false)
  const [rsvpPending, setRsvpPending] = useState(false)
  const [plusOne, setPlusOne] = useState(0)

  useEffect(() => {
    if (!token) return
    setLoading(true)
    invitationsAPI.viewPublic(token)
      .then((data) => setInvitation(data))
      .catch((err) => {
        if (err.response?.status === 410) setError('تم إلغاء هذه الدعوة')
        else if (err.response?.status === 404) setError('الدعوة غير موجودة')
        else setError('حدث خطأ أثناء تحميل الدعوة')
      })
      .finally(() => setLoading(false))
  }, [token])

  const handleRsvp = async (status: 'accepted' | 'declined') => {
    if (!token) return
    setRsvpPending(true)
    try {
      await invitationsAPI.rsvp(token, { status, plus_one_count: plusOne })
      setRsvpDone(true)
      setInvitation((prev) => prev ? { ...prev, rsvp_status: status } : prev)
    } catch {
      // Ignore errors for now
    }
    setRsvpPending(false)
  }

  if (loading) {
    return (
      <div className="pub-page pub-page--loading">
        <Loader2 size={40} className="animate-spin" style={{ color: '#C9A96E' }} />
      </div>
    )
  }

  if (error) {
    return (
      <div className="pub-page">
        <div className="pub-error">
          <XCircle size={48} style={{ color: '#ef4444' }} />
          <h2>{error}</h2>
        </div>
      </div>
    )
  }

  if (!invitation) return null

  const inv = invitation
  const isVip = inv.ticket_class === 'vip'

  return (
    <div className="pub-page">
      <div className="pub-card">
        {/* Cover or Rendered Card */}
        {inv.card_image_url || inv.render_image_url ? (
          <div className="pub-card__cover">
            <img src={inv.card_image_url || inv.render_image_url!} alt="دعوة" />
          </div>
        ) : inv.cover_image_url ? (
          <div className="pub-card__cover">
            <img src={inv.cover_image_url} alt="غلاف الحدث" />
          </div>
        ) : null}

        {/* Header */}
        <div className="pub-card__header">
          {isVip && (
            <span className="pub-vip-badge"><Sparkles size={14} /> VIP</span>
          )}
          <h1>{inv.event_title_ar || inv.event_title}</h1>
          {inv.guest_name_ar || inv.guest_name ? (
            <p className="pub-guest-name">{inv.guest_name_ar || inv.guest_name}</p>
          ) : null}
        </div>

        {/* Event Details */}
        <div className="pub-details">
          {inv.start_date && (
            <div className="pub-detail-item">
              <CalendarDays size={18} />
              <div>
                <span className="pub-detail-label">التاريخ</span>
                <span className="pub-detail-value">
                  {new Date(inv.start_date).toLocaleDateString('ar', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
                </span>
              </div>
            </div>
          )}
          {inv.start_date && (
            <div className="pub-detail-item">
              <Clock size={18} />
              <div>
                <span className="pub-detail-label">الوقت</span>
                <span className="pub-detail-value">
                  {new Date(inv.start_date).toLocaleTimeString('ar', { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
            </div>
          )}
          {(inv.venue_name_ar || inv.venue_name) && (
            <div className="pub-detail-item">
              <MapPin size={18} />
              <div>
                <span className="pub-detail-label">المكان</span>
                <span className="pub-detail-value">{inv.venue_name_ar || inv.venue_name}</span>
                {inv.venue_address && <span className="pub-detail-sub">{inv.venue_address}</span>}
              </div>
            </div>
          )}
        </div>

        {/* Seating info */}
        {(inv.seat_number || inv.table_number || inv.hall) && (
          <div className="pub-seating">
            {inv.hall && <span>قاعة: <strong>{inv.hall}</strong></span>}
            {inv.table_number && <span>طاولة: <strong>{inv.table_number}</strong></span>}
            {inv.seat_number && <span>مقعد: <strong>{inv.seat_number}</strong></span>}
          </div>
        )}

        {/* QR Code */}
        {inv.barcode_png_url && (
          <div className="pub-qr">
            <img src={inv.barcode_png_url} alt="QR Code" />
            <span>أظهر هذا الرمز عند الدخول</span>
          </div>
        )}

        {/* Map Link */}
        {inv.venue_map_url && (
          <a href={inv.venue_map_url} target="_blank" rel="noopener noreferrer" className="pub-map-link">
            <MapPin size={16} /> عرض الموقع على الخريطة
            <ExternalLink size={14} />
          </a>
        )}

        {/* RSVP */}
        {inv.allow_rsvp && !rsvpDone && inv.rsvp_status !== 'accepted' && inv.rsvp_status !== 'declined' && (
          <div className="pub-rsvp">
            <h3>هل ستحضر؟</h3>
            {inv.allow_plus_one && (
              <div className="pub-rsvp-plus">
                <label>عدد المرافقين:</label>
                <input
                  type="number" min={0} max={10} value={plusOne}
                  onChange={(e) => setPlusOne(parseInt(e.target.value) || 0)}
                />
              </div>
            )}
            <div className="pub-rsvp-actions">
              <button
                className="pub-rsvp-btn pub-rsvp-btn--accept"
                onClick={() => handleRsvp('accepted')}
                disabled={rsvpPending}
              >
                <CheckCircle2 size={18} /> نعم، سأحضر
              </button>
              <button
                className="pub-rsvp-btn pub-rsvp-btn--decline"
                onClick={() => handleRsvp('declined')}
                disabled={rsvpPending}
              >
                <XCircle size={18} /> لا، أعتذر
              </button>
            </div>
          </div>
        )}

        {/* RSVP Done */}
        {(rsvpDone || inv.rsvp_status === 'accepted' || inv.rsvp_status === 'declined') && (
          <div className={`pub-rsvp-result ${inv.rsvp_status === 'accepted' ? 'pub-rsvp-result--accepted' : 'pub-rsvp-result--declined'}`}>
            {inv.rsvp_status === 'accepted' ? (
              <><CheckCircle2 size={20} /> تم تأكيد حضورك — نتشرف بلقائك!</>
            ) : (
              <><XCircle size={20} /> شكراً لتبليغنا — نتمنى لقاءك في مناسبة أخرى</>
            )}
          </div>
        )}

        {/* Footer */}
        <div className="pub-footer">
          <span>مدعوم بواسطة Qentry</span>
        </div>
      </div>
    </div>
  )
}
