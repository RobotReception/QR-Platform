/**
 * CheckinPage.tsx
 * QR scanning and live event attendance tracking.
 */
import { useState, useRef } from 'react'
import { QrCode, Search, Loader2 } from 'lucide-react'
import { WorkspaceShell } from '@features/workspace/components/WorkspaceShell'
import { useAuthStore } from '@features/auth/store/authStore'
import { useEventsList } from '@features/events/hooks/useEvents'
import { useScanCheckin, useLiveStats } from '../hooks/useCheckin'
import { ScanResult } from '../components/ScanResult'
import { LiveStatsPanel } from '../components/LiveStatsPanel'
import type { CheckinResponse } from '../api/checkinApi'
import './checkin.css'

export default function CheckinPage() {
  const tenantId = useAuthStore((s) => s.currentTenantId)
  const [selectedEvent, setSelectedEvent] = useState('')
  const [tokenInput, setTokenInput] = useState('')
  const [lastResult, setLastResult] = useState<CheckinResponse | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const { data: events } = useEventsList(tenantId || '', '')
  const scanMutation = useScanCheckin()
  const { data: liveStats, isLoading: statsLoading } = useLiveStats(selectedEvent)

  const handleScan = (e: React.FormEvent) => {
    e.preventDefault()
    if (!tokenInput.trim()) return

    // Extract token from URL or raw input
    let token = tokenInput.trim()
    const urlMatch = token.match(/\/i\/([a-f0-9]+)/i)
    if (urlMatch) token = urlMatch[1]

    scanMutation.mutate(
      {
        token,
        event_id: selectedEvent || undefined,
        scan_method: 'qr',
      },
      {
        onSuccess: (result) => {
          setLastResult(result)
          setTokenInput('')
          inputRef.current?.focus()
        },
      }
    )
  }

  if (!tenantId) {
    return (
      <WorkspaceShell title="تسجيل الحضور" subtitle="">
        <div className="dash-state">
          <QrCode size={40} />
          <h1>لا توجد مساحة عمل محددة</h1>
          <p>اختر مساحة العمل أولاً لعرض الأحداث والبدء في تسجيل الحضور.</p>
        </div>
      </WorkspaceShell>
    )
  }

  return (
    <WorkspaceShell
      title="تسجيل الحضور"
      subtitle="مسح QR Code أو إدخال رمز الدعوة يدوياً"
    >
      {/* Event Selector */}
      <div className="checkin-event-bar">
        <label>الحدث:</label>
        <select
          value={selectedEvent}
          onChange={(e) => { setSelectedEvent(e.target.value); setLastResult(null) }}
          className="inv-filter-select checkin-event-select"
        >
          <option value="">اختر الحدث</option>
          {events?.map((ev) => (
            <option key={ev.id} value={ev.id}>{ev.title}</option>
          ))}
        </select>
      </div>

      {/* Scanner */}
      <div className="checkin-scanner-section">
        <div className="checkin-scanner-card">
          <div className="checkin-scanner-icon">
            <QrCode size={40} />
          </div>
          <h3>مسح رمز الدعوة</h3>
          <p>أدخل رمز الدعوة أو قم بمسح QR Code باستخدام قارئ QR</p>

          <form onSubmit={handleScan} className="checkin-scan-form">
            <div className="checkin-scan-input-wrap">
              <Search size={18} className="checkin-scan-icon" />
              <input
                ref={inputRef}
                type="text"
                placeholder="أدخل رمز الدعوة أو امسح QR..."
                value={tokenInput}
                onChange={(e) => setTokenInput(e.target.value)}
                autoFocus
                dir="ltr"
                className="checkin-scan-input"
              />
            </div>
            <button
              type="submit"
              className="btn btn-primary checkin-scan-btn"
              disabled={scanMutation.isPending || !tokenInput.trim()}
            >
              {scanMutation.isPending ? (
                <Loader2 size={18} className="animate-spin" />
              ) : (
                'تحقق'
              )}
            </button>
          </form>
        </div>

        {/* Scan Result */}
        <ScanResult result={lastResult} />
      </div>

      {/* Live Stats */}
      {selectedEvent && (
        <LiveStatsPanel stats={liveStats} isLoading={statsLoading} />
      )}
    </WorkspaceShell>
  )
}
