export function DashboardSkeleton() {
  return (
    <div className="dash-skeleton" aria-busy="true" aria-label="جار تحميل لوحة التحكم">
      {/* stat cards */}
      <div className="dash-skeleton__stats">
        {[...Array(4)].map((_, i) => (
          <div className="skel-card" key={i}>
            <div className="skel-circle" />
            <div className="skel-lines">
              <div className="skel-line skel-line--sm" />
              <div className="skel-line skel-line--lg" />
              <div className="skel-line skel-line--md" />
            </div>
          </div>
        ))}
      </div>

      {/* main grid */}
      <div className="dash-skeleton__grid">
        <div className="skel-panel skel-panel--wide">
          <div className="skel-line skel-line--sm" />
          <div className="skel-line skel-line--lg" />
          <div className="skel-bar" />
          <div className="skel-bar" />
          <div className="skel-bar" />
          <div className="skel-split">
            <div className="skel-box" />
            <div className="skel-box" />
            <div className="skel-box" />
          </div>
        </div>
        <div className="skel-panel">
          <div className="skel-line skel-line--sm" />
          <div className="skel-line skel-line--lg" />
          <div className="skel-circle skel-circle--big" />
        </div>
      </div>

      {/* secondary grid */}
      <div className="dash-skeleton__tri">
        {[...Array(3)].map((_, i) => (
          <div className="skel-panel" key={i}>
            <div className="skel-line skel-line--sm" />
            <div className="skel-line skel-line--lg" />
            <div className="skel-row" />
            <div className="skel-row" />
            <div className="skel-row" />
          </div>
        ))}
      </div>
    </div>
  )
}
