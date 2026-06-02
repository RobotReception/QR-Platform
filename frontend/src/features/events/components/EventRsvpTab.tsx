/**
 * EventRsvpTab.tsx
 * Tab for Event RSVP Management inside EventDetailsPage.
 * Shows stats, filters, manual updates, and CSV exports.
 */
import { useState, useMemo } from 'react'
import {
  Search, Users, CheckCircle2, XCircle, Clock,
  UserPlus, Download, Loader2, RefreshCw, AlertCircle,
  Eye, Send, Copy
} from 'lucide-react'
import { useInvitationsList, useUpdateInvitation } from '@features/invitations/hooks/useInvitations'
import type { RsvpStatus, TicketClass, Invitation } from '@features/invitations/types'
import { RsvpDetailPanel } from './RsvpDetailPanel'
import './event-rsvp-tab.css'

interface Props {
  eventId: string
  allowRsvp?: boolean
}

export function EventRsvpTab({ eventId, allowRsvp = true }: Props) {
  const [search, setSearch] = useState('')
  const [rsvpFilter, setRsvpFilter] = useState<string>('all')
  const [classFilter, setClassFilter] = useState<TicketClass | 'all'>('all')
  const [updatingId, setUpdatingId] = useState<string | null>(null)
  const [selectedInv, setSelectedInv] = useState<Invitation | null>(null)

  // ── Data Query ──
  const { data: invitations, isLoading, isError, refetch } = useInvitationsList({
    event_id: eventId,
    limit: 500,
  })

  // ── Sync active selected invitation with updated refetched data ──
  const rsvpInvitations = useMemo(() => {
    if (!invitations) return []
    return invitations.filter((inv) => {
      const isFromForm = inv.metadata && (inv.metadata.is_registration === true || inv.metadata.custom_fields !== undefined)
      if (isFromForm) return false
      
      // If it's explicitly marked as require_rsvp
      if (inv.metadata?.require_rsvp === true) return true
      if (inv.metadata?.require_rsvp === false) return false

      // Fallback for legacy data: if it's not a form, and it was created as RSVP.
      // RSVP manual invites were created as 'created'/'pending' rsvp_status.
      // Direct invites were created as 'accepted'/'accepted' directly.
      return (
        inv.rsvp_status === 'pending' ||
        inv.rsvp_status === 'declined' ||
        (inv.rsvp_status === 'accepted' && (inv.status === 'viewed' || inv.status === 'sent' || inv.status === 'created'))
      )
    })
  }, [invitations])

  const activeSelectedInv = useMemo(() => {
    if (!selectedInv || !rsvpInvitations) return null
    return rsvpInvitations.find((i) => i.id === selectedInv.id) || null
  }, [selectedInv, rsvpInvitations])

  const updateMutation = useUpdateInvitation()

  // ── Stats Calculations ──
  const stats = useMemo(() => {
    if (!rsvpInvitations) return { total: 0, accepted: 0, declined: 0, pending: 0, plusOnes: 0, viewed: 0, sent: 0, unopened: 0 }
    
    let accepted = 0
    let declined = 0
    let pending = 0
    let plusOnes = 0
    let viewed = 0
    let sent = 0
    let unopened = 0

    rsvpInvitations.forEach((inv) => {
      // RSVP stats
      const status = inv.rsvp_status || 'pending'
      if (status === 'accepted') {
        accepted++
        plusOnes += inv.plus_one_count || 0
      } else if (status === 'declined') {
        declined++
      } else {
        pending++
      }

      // Delivery stats
      if (inv.status === 'viewed' || inv.status === 'accepted' || inv.status === 'declined' || inv.status === 'checked_in') {
        viewed++
      } else if (inv.status === 'sent') {
        sent++
      } else if (inv.status === 'created') {
        unopened++
      }
    })

    return {
      total: rsvpInvitations.length,
      accepted,
      declined,
      pending,
      plusOnes,
      viewed,
      sent,
      unopened,
    }
  }, [rsvpInvitations])

  // ── Search & Filter ──
  const filtered = useMemo(() => {
    if (!rsvpInvitations) return []
    return rsvpInvitations.filter((inv) => {
      // Search match
      const q = search.toLowerCase().trim()
      const matchesSearch = !q ||
        inv.guest_name?.toLowerCase().includes(q) ||
        inv.guest_name_ar?.includes(q) ||
        inv.guest_phone?.includes(q) ||
        inv.token?.includes(q)

      // RSVP Status / Delivery Filter
      const matchesRsvp = allowRsvp
        ? (rsvpFilter === 'all' || (inv.rsvp_status || 'pending') === rsvpFilter)
        : (rsvpFilter === 'all' || 
            (rsvpFilter === 'viewed' && (inv.status === 'viewed' || inv.status === 'accepted' || inv.status === 'declined' || inv.status === 'checked_in')) ||
            (rsvpFilter === 'sent' && inv.status === 'sent') ||
            (rsvpFilter === 'created' && inv.status === 'created')
          )

      // Ticket Class Filter
      const matchesClass = classFilter === 'all' || inv.ticket_class === classFilter

      return matchesSearch && matchesRsvp && matchesClass
    })
  }, [rsvpInvitations, search, rsvpFilter, classFilter, allowRsvp])

  // ── Export CSV ──
  const handleExportCSV = () => {
    if (!filtered || filtered.length === 0) return
    
    const headers = allowRsvp
      ? ["الاسم", "الهاتف", "فئة التذكرة", "حالة تأكيد الحضور", "عدد المرافقين", "تاريخ الرد", "الرسالة"]
      : ["الاسم", "الهاتف", "فئة التذكرة", "حالة المشاهدة", "تاريخ العرض والتسليم"]

    const rows = filtered.map(inv => {
      if (allowRsvp) {
        return [
          inv.guest_name_ar || inv.guest_name || '',
          inv.guest_phone || '',
          inv.ticket_class === 'vip' ? 'VIP' : 'عادي',
          inv.rsvp_status === 'accepted' ? 'مقبول' : inv.rsvp_status === 'declined' ? 'مرفوض' : 'قيد الانتظار',
          inv.plus_one_count || 0,
          inv.rsvp_at ? new Date(inv.rsvp_at).toLocaleString('ar-SA') : '',
          inv.rsvp_message || ''
        ]
      } else {
        const isOpened = inv.status === 'viewed' || inv.status === 'accepted' || inv.status === 'declined' || inv.status === 'checked_in'
        const isSent = inv.status === 'sent'
        const statusLabel = isOpened ? 'تمت المشاهدة' : (isSent ? 'تم الإرسال' : 'لم ترسل بعد')
        const viewDate = isOpened ? new Date(inv.updated_at).toLocaleString('ar-SA') : ''
        return [
          inv.guest_name_ar || inv.guest_name || '',
          inv.guest_phone || '',
          inv.ticket_class === 'vip' ? 'VIP' : 'عادي',
          statusLabel,
          viewDate
        ]
      }
    })
    
    // Excel-friendly UTF-8 BOM
    const csvContent = "\uFEFF" + [
      headers.map(h => `"${h}"`).join(','), 
      ...rows.map(r => r.map(val => `"${String(val).replace(/"/g, '""')}"`).join(','))
    ].join('\r\n')
    
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a")
    link.setAttribute("href", url)
    link.setAttribute("download", `تقرير_ RSVP_الحدث_${eventId}.csv`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  // ── Manual RSVP Update ──
  const handleManualRsvp = async (
    id: string,
    status: RsvpStatus,
    plusOneCount?: number,
    messageText?: string | null,
    guestCount?: number
  ) => {
    setUpdatingId(id)
    try {
      const invStatus = status === 'accepted' ? 'accepted' : (status === 'declined' ? 'declined' : 'created')
      
      // Preserve existing parameters if not explicitly provided
      const current = invitations?.find(i => i.id === id)
      const pCount = plusOneCount !== undefined ? plusOneCount : (status === 'accepted' ? (current?.plus_one_count || 0) : 0)
      const msg = messageText !== undefined ? messageText : (current?.rsvp_message || null)
      const gCount = guestCount !== undefined ? guestCount : (current?.guest_count || 1)

      await updateMutation.mutateAsync({
        id,
        data: {
          rsvp_status: status,
          status: invStatus,
          plus_one_count: pCount,
          rsvp_message: msg,
          guest_count: gCount,
          rsvp_at: status === 'pending' ? null : new Date().toISOString()
        }
      })
    } catch {
      // Ignore errors for now
    } finally {
      setUpdatingId(null)
    }
  }

  if (isLoading) {
    return (
      <div className="rsvp-loading">
        <Loader2 size={36} className="spin" />
        <span>جاري تحميل بيانات تأكيد الحضور...</span>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="rsvp-error">
        <AlertCircle size={40} />
        <h3>فشل تحميل البيانات</h3>
        <p>يرجى التحقق من اتصالك بالإنترنت وإعادة المحاولة.</p>
        <button className="btn btn-primary" onClick={() => refetch()}>
          <RefreshCw size={16} />
          إعادة المحاولة
        </button>
      </div>
    )
  }

  return (
    <div className="rsvp-tab-content">
      {/* ── Metric Cards ── */}
      <div className="rsvp-metrics-grid">
        <div className="rsvp-metric-card">
          <div className="rsvp-metric-card__header">
            <Users size={18} style={{ color: 'var(--color-primary)' }} />
            <span>إجمالي الدعوات</span>
          </div>
          <strong>{stats.total}</strong>
        </div>

        {allowRsvp ? (
          <>
            <div className="rsvp-metric-card rsvp-metric-card--accepted">
              <div className="rsvp-metric-card__header">
                <CheckCircle2 size={18} style={{ color: '#10b981' }} />
                <span>حضور مؤكد</span>
              </div>
              <strong>{stats.accepted}</strong>
            </div>
            <div className="rsvp-metric-card rsvp-metric-card--declined">
              <div className="rsvp-metric-card__header">
                <XCircle size={18} style={{ color: '#ef4444' }} />
                <span>اعتذروا عن الحضور</span>
              </div>
              <strong>{stats.declined}</strong>
            </div>
            <div className="rsvp-metric-card rsvp-metric-card--pending">
              <div className="rsvp-metric-card__header">
                <Clock size={18} style={{ color: '#94a3b8' }} />
                <span>بانتظار الرد</span>
              </div>
              <strong>{stats.pending}</strong>
            </div>
            <div className="rsvp-metric-card">
              <div className="rsvp-metric-card__header">
                <UserPlus size={18} style={{ color: '#3b82f6' }} />
                <span>المرافقين (Plus-One)</span>
              </div>
              <strong>{stats.plusOnes}</strong>
            </div>
          </>
        ) : (
          <>
            <div className="rsvp-metric-card rsvp-metric-card--accepted">
              <div className="rsvp-metric-card__header">
                <Eye size={18} style={{ color: '#10b981' }} />
                <span>تمت المشاهدة</span>
              </div>
              <strong>{stats.viewed}</strong>
            </div>
            <div className="rsvp-metric-card" style={{ borderLeft: '4px solid #3b82f6' }}>
              <div className="rsvp-metric-card__header">
                <Send size={18} style={{ color: '#3b82f6' }} />
                <span>تم الإرسال والتسليم</span>
              </div>
              <strong>{stats.sent}</strong>
            </div>
            <div className="rsvp-metric-card rsvp-metric-card--pending">
              <div className="rsvp-metric-card__header">
                <Clock size={18} style={{ color: '#94a3b8' }} />
                <span>لم تفتح بعد</span>
              </div>
              <strong>{stats.unopened}</strong>
            </div>
          </>
        )}
      </div>

      {/* ── Filters and Actions Toolbar ── */}
      <div className="rsvp-toolbar-panel">
        <div className="rsvp-search-box">
          <Search size={16} />
          <input
            type="text"
            placeholder="بحث بالاسم أو الهاتف..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div className="rsvp-filters-row">
          <select
            value={rsvpFilter}
            onChange={(e) => setRsvpFilter(e.target.value as any)}
            className="rsvp-filter-dropdown"
          >
            {allowRsvp ? (
              <>
                <option value="all">كل الحالات (RSVP)</option>
                <option value="accepted">مؤكد الحضور</option>
                <option value="declined">المعتذرين</option>
                <option value="pending">بانتظار الرد</option>
              </>
            ) : (
              <>
                <option value="all">كل الحالات (المشاهدة)</option>
                <option value="viewed">تمت المشاهدة</option>
                <option value="sent">تم الإرسال</option>
                <option value="created">لم ترسل بعد</option>
              </>
            )}
          </select>

          <select
            value={classFilter}
            onChange={(e) => setClassFilter(e.target.value as any)}
            className="rsvp-filter-dropdown"
          >
            <option value="all">كل الفئات</option>
            <option value="vip">VIP</option>
            <option value="normal">عادي</option>
          </select>

          <button
            className="btn btn-ghost"
            onClick={handleExportCSV}
            disabled={filtered.length === 0}
          >
            <Download size={15} />
            <span>تصدير Excel</span>
          </button>
        </div>
      </div>

      {/* ── RSVP List Table ── */}
      {filtered.length === 0 ? (
        <div className="rsvp-empty-state">
          <Users size={40} style={{ opacity: 0.3 }} />
          <h4>لا توجد نتائج تطابق خيارات التصفية</h4>
          <p>تأكد من كتابة الاسم بشكل صحيح أو تغيير خيارات التصفية.</p>
        </div>
      ) : (
        <div className="rsvp-table-container">
          <table className="rsvp-table">
            <thead>
              {allowRsvp ? (
                <tr>
                  <th>الاسم</th>
                  <th>الهاتف</th>
                  <th>فئة التذكرة</th>
                  <th>حالة RSVP</th>
                  <th>المرافقين</th>
                  <th>قراءة الباركود</th>
                  <th>تاريخ الرد</th>
                  <th>رسالة الضيف</th>
                  <th>إجراءات يدوية</th>
                </tr>
              ) : (
                <tr>
                  <th>الاسم</th>
                  <th>الهاتف</th>
                  <th>فئة التذكرة</th>
                  <th>حالة الدعوة</th>
                  <th>تاريخ الفتح والمشاهدة</th>
                  <th>قراءة الباركود</th>
                  <th>إجراءات سريعة</th>
                </tr>
              )}
            </thead>
            <tbody>
              {filtered.map((inv) => {
                const status = inv.rsvp_status || 'pending'
                const isOpened = inv.status === 'viewed' || inv.status === 'accepted' || inv.status === 'declined' || inv.status === 'checked_in'
                const isSent = inv.status === 'sent'

                return (
                  <tr key={inv.id} onClick={() => setSelectedInv(inv)}>
                    <td className="rsvp-td-name">
                      <strong>{inv.guest_name_ar || inv.guest_name || 'ضيف بدون اسم'}</strong>
                    </td>
                    <td>{inv.guest_phone || <span className="rsvp-txt-muted">—</span>}</td>
                    <td>
                      <span className={`rsvp-class-badge rsvp-class-badge--${inv.ticket_class}`}>
                        {inv.ticket_class === 'vip' ? 'VIP' : 'عادي'}
                      </span>
                    </td>

                    {allowRsvp ? (
                      <>
                        <td>
                          <span className={`rsvp-status-badge rsvp-status-badge--${status}`}>
                            {status === 'accepted' ? 'مقبول' : status === 'declined' ? 'معتذر' : 'لم يرد بعد'}
                          </span>
                        </td>
                        <td className="rsvp-td-center">
                          {status === 'accepted' ? inv.plus_one_count || 0 : <span className="rsvp-txt-muted">—</span>}
                        </td>
                        <td>
                          {inv.checkin_count > 0 ? (
                            <span className="rsvp-status-badge rsvp-status-badge--accepted" style={{ background: 'rgba(16, 185, 129, 0.08)', color: '#10b981', borderColor: 'rgba(16, 185, 129, 0.15)' }}>
                              تم الدخول ({inv.checkin_count})
                            </span>
                          ) : (
                            <span className="rsvp-status-badge rsvp-status-badge--pending" style={{ color: '#94a3b8', background: 'rgba(148, 163, 184, 0.08)', borderColor: 'rgba(148, 163, 184, 0.15)' }}>
                              لم يحضر
                            </span>
                          )}
                        </td>
                        <td>
                          {inv.rsvp_at ? (
                            <span className="rsvp-date-txt">
                              {new Date(inv.rsvp_at).toLocaleDateString('ar-SA')}
                            </span>
                          ) : (
                            <span className="rsvp-txt-muted">—</span>
                          )}
                        </td>
                        <td className="rsvp-td-message" title={inv.rsvp_message || ''}>
                          {inv.rsvp_message ? (
                            <span>{inv.rsvp_message}</span>
                          ) : (
                            <span className="rsvp-txt-muted">—</span>
                          )}
                        </td>
                        <td>
                          <div className="rsvp-action-btns">
                            {updatingId === inv.id ? (
                              <Loader2 size={16} className="spin" style={{ color: 'var(--color-primary)' }} />
                            ) : (
                              <>
                                {status !== 'accepted' && (
                                  <button
                                    className="rsvp-action-icon rsvp-action-icon--accept"
                                    onClick={(e) => { e.stopPropagation(); handleManualRsvp(inv.id, 'accepted'); }}
                                    title="تأكيد حضور الضيف يدوياً"
                                  >
                                    <CheckCircle2 size={15} />
                                  </button>
                                )}
                                {status !== 'declined' && (
                                  <button
                                    className="rsvp-action-icon rsvp-action-icon--decline"
                                    onClick={(e) => { e.stopPropagation(); handleManualRsvp(inv.id, 'declined'); }}
                                    title="تسجيل اعتذار الضيف يدوياً"
                                  >
                                    <XCircle size={15} />
                                  </button>
                                )}
                                {status !== 'pending' && (
                                  <button
                                    className="rsvp-action-icon rsvp-action-icon--reset"
                                    onClick={(e) => { e.stopPropagation(); handleManualRsvp(inv.id, 'pending'); }}
                                    title="إعادة تعيين وبانتظار الرد"
                                  >
                                    <Clock size={15} />
                                  </button>
                                )}
                              </>
                            )}
                          </div>
                        </td>
                      </>
                    ) : (
                      <>
                        <td>
                          {isOpened ? (
                            <span className="rsvp-status-badge rsvp-status-badge--accepted">
                              تمت المشاهدة
                            </span>
                          ) : isSent ? (
                            <span className="rsvp-status-badge rsvp-status-badge--pending" style={{ color: '#3b82f6', background: 'rgba(59, 130, 246, 0.08)', borderColor: 'rgba(59, 130, 246, 0.15)' }}>
                              تم الإرسال
                            </span>
                          ) : (
                            <span className="rsvp-status-badge rsvp-status-badge--pending">
                              لم ترسل بعد
                            </span>
                          )}
                        </td>
                        <td>
                          {isOpened ? (
                            <span className="rsvp-date-txt">
                              {new Date(inv.updated_at).toLocaleDateString('ar-SA')} {new Date(inv.updated_at).toLocaleTimeString('ar-SA', { hour: '2-digit', minute: '2-digit' })}
                            </span>
                          ) : (
                            <span className="rsvp-txt-muted">—</span>
                          )}
                        </td>
                        <td>
                          {inv.checkin_count > 0 ? (
                            <span className="rsvp-status-badge rsvp-status-badge--accepted" style={{ background: 'rgba(16, 185, 129, 0.08)', color: '#10b981', borderColor: 'rgba(16, 185, 129, 0.15)' }}>
                              تم الدخول ({inv.checkin_count})
                            </span>
                          ) : (
                            <span className="rsvp-status-badge rsvp-status-badge--pending" style={{ color: '#94a3b8', background: 'rgba(148, 163, 184, 0.08)', borderColor: 'rgba(148, 163, 184, 0.15)' }}>
                              لم يحضر
                            </span>
                          )}
                        </td>
                        <td>
                          <div className="rsvp-action-btns">
                            <button
                              className="rsvp-action-icon"
                              onClick={(e) => {
                                e.stopPropagation();
                                navigator.clipboard.writeText(`${window.location.origin}/i/${inv.token}`);
                              }}
                              title="نسخ رابط كرت الدعوة للضيف"
                            >
                              <Copy size={15} />
                            </button>
                          </div>
                        </td>
                      </>
                    )}
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Guest RSVP Detail Side Panel ── */}
      <RsvpDetailPanel
        invitation={activeSelectedInv}
        onClose={() => setSelectedInv(null)}
        onUpdateRsvp={handleManualRsvp}
        isUpdating={updatingId !== null}
        allowRsvp={allowRsvp}
      />
    </div>
  )
}
