import React from 'react'

interface RsvpSectionProps {
  requireRsvp: boolean
  setRequireRsvp: (val: boolean) => void
  isMissingContact: boolean
  missingContactCount: number
  missingContactSourceLabel: string
  style?: React.CSSProperties
}

export function RsvpSection({
  requireRsvp,
  setRequireRsvp,
  isMissingContact,
  missingContactCount,
  missingContactSourceLabel,
  style,
}: RsvpSectionProps) {
  return (
    <>
      <div
        className={`toggle-row ${requireRsvp ? 'toggle-row--on' : ''}`}
        onClick={() => setRequireRsvp(!requireRsvp)}
        style={{ cursor: 'pointer', ...style }}
      >
        <div className="toggle-row-info">
          <h4 style={{ margin: 0, fontSize: '14px', fontWeight: '600', color: '#fff' }}>
            تفعيل ميزة تأكيد الحضور (RSVP)
          </h4>
          <p style={{ margin: '4px 0 0 0', fontSize: '12px', color: 'rgba(255,255,255,0.5)' }}>
            عند تفعيلها، سيُطلب من الضيوف تأكيد حضورهم أولاً لتنتقل الدعوات للدعوات النهائية.
          </p>
        </div>
        <div className={`toggle-switch ${requireRsvp ? 'toggle-switch--on' : ''}`}>
          <div className="toggle-switch__thumb" />
        </div>
      </div>

      {isMissingContact && (
        <div
          className="inv-import-card"
          style={{
            marginTop: '12px',
            marginBottom: '16px',
            border: '1px dashed #ef4444',
            padding: '16px',
            borderRadius: '8px',
            background: 'rgba(239, 68, 68, 0.05)',
          }}
        >
          <div
            className="inv-import-card__header"
            style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '16px' }}
          >
            <div>
              <strong style={{ color: '#f87171', fontSize: '14px' }}>
                مطلوب ملف بيانات الضيوف (الاسم، الجوال/البريد) لتفعيل تأكيد الحضور
              </strong>
              <span style={{ color: 'rgba(255,255,255,0.6)', marginTop: '4px', display: 'block', fontSize: '12px' }}>
                تأكيد الحضور يتطلب أرقام جوال أو إيميلات لإرسال الدعوات. يرجى رفع ملف Excel يحتوي على بيانات الضيوف.
              </span>
              <span style={{ color: '#60a5fa', marginTop: '6px', display: 'block', fontSize: '12px', fontWeight: 'bold' }}>
                عدد الصفوف المطلوبة في الملف: {missingContactCount} صفوف ({missingContactSourceLabel})
              </span>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
