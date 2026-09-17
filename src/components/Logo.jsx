/**
 * SRMIST Fab Lab emblem.
 *
 * This is a stand-in mark drawn to match the console's visual language —
 * it is NOT the official SRMIST logo. Replace `Mark` with the licensed
 * institutional asset before any public or official use; everything else
 * (layout, sizing, the lockup) can stay as-is.
 */
export function LogoMark({ size = 34, className = '' }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      className={className}
      role="img"
      aria-label="SRMIST Fab Lab"
    >
      <defs>
        <linearGradient id="aams-mark" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#38bdf8" />
          <stop offset="55%" stopColor="#22d3ee" />
          <stop offset="100%" stopColor="#a78bfa" />
        </linearGradient>
      </defs>

      {/* Shield body */}
      <path
        d="M24 3.5 41 8.5v14.2c0 10.4-6.9 17.6-17 21.8-10.1-4.2-17-11.4-17-21.8V8.5z"
        fill="url(#aams-mark)"
        fillOpacity="0.14"
        stroke="url(#aams-mark)"
        strokeWidth="1.7"
        strokeLinejoin="round"
      />

      {/* Inner monogram */}
      <text
        x="24"
        y="27.5"
        textAnchor="middle"
        fontFamily="'Space Grotesk', 'Segoe UI', system-ui, sans-serif"
        fontSize="14.5"
        fontWeight="700"
        letterSpacing="0.5"
        fill="url(#aams-mark)"
      >
        SRM
      </text>

      {/* Baseline rule under the monogram */}
      <rect x="15" y="31.5" width="18" height="1.4" rx="0.7" fill="url(#aams-mark)" opacity="0.75" />
    </svg>
  )
}

/** Emblem + wordmark, for the sidebar brand block. */
export function LogoLockup({ markSize = 34 }) {
  return (
    <div className="brand-lockup">
      <span className="brand-emblem">
        <LogoMark size={markSize} />
      </span>
      <span className="brand-text">
        <span className="brand-inst">SRMIST</span>
        <span className="brand-dept">Fab Lab · AAMS</span>
      </span>
    </div>
  )
}

export default LogoMark
