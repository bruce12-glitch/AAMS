/**
 * FABLAB brand mark — geometric, cyan → teal gradient.
 *
 * The FABLAB wordmark from the lab's own brand kit, redrawn in SVG so it
 * scales cleanly and inherits `currentColor` where needed. The distinctive
 * triangular A's and stacked B's are preserved. Swap this file for the
 * official licensed asset when one is available; the layout (LogoLockup)
 * is unchanged.
 */

/** Gradient used by the wordmark. Defined once so each <use> reuses it. */
function FablabGradient({ id = 'fablab-mark' }) {
  return (
    <defs>
      <linearGradient id={id} x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stopColor="#22d3ee" />
        <stop offset="60%" stopColor="#14b8a6" />
        <stop offset="100%" stopColor="#2dd4bf" />
      </linearGradient>
    </defs>
  )
}

/**
 * "FABLAB" wordmark. Custom paths per letter to keep the angular A and
 * twin-bump B consistent at every size. ViewBox is sized for a 1:3 aspect
 * so the mark sits comfortably next to body text.
 */
export function FablabMark({ size = 140, className = '', id = 'fablab-mark' }) {
  return (
    <svg
      width={size}
      height={(size / 184) * 44}
      viewBox="0 0 184 44"
      className={className}
      role="img"
      aria-label="FABLAB"
    >
      <FablabGradient id={id} />
      <g fill={`url(#${id})`}>
        {/* F */}
        <path d="M0 0 H22 V5 H5 V18 H18 V23 H5 V40 H0 Z" />
        {/* A — solid triangle with a lower-V cutout (even-odd fill) */}
        <path
          fillRule="evenodd"
          d="M32 40 L46 0 L60 40 Z M37 40 L46 13 L55 40 Z"
        />
        {/* B — left bar + top bump + bottom bump */}
        <path d="M64 0 H78 a9 9 0 0 1 0 18 H69 V17 H77 a9 9 0 0 1 0 18 H69 V40 H64 Z" />
        {/* L */}
        <path d="M96 0 H101 V35 H119 V40 H96 Z" />
        {/* A — second one */}
        <path
          fillRule="evenodd"
          d="M124 40 L138 0 L152 40 Z M129 40 L138 13 L147 40 Z"
        />
        {/* B — final */}
        <path d="M156 0 H170 a9 9 0 0 1 0 18 H161 V17 H169 a9 9 0 0 1 0 18 H161 V40 H156 Z" />
      </g>
    </svg>
  )
}

/**
 * Institutional logos strip — placeholder text badges for the four logos
 * shown above the SRM DEI page (DEI, SRMIST, Moothstrapper, Birac BioNEST).
 *
 * Replace each label slot with an <img src="..." /> when the licensed
 * institutional assets are available. The grid, hover treatment, and
 * sizing will still work.
 */
/**
 * Header magnifier behaviour: every list page (Members, Entry Logs, …) has
 * its own `.search-input` that filters as you type, but the header icon did
 * nothing when clicked. It now focuses the current page's search field (with
 * a brief brass flash so you can see which field caught it); on pages with
 * no search field it jumps to Entry Logs and focuses that one instead.
 */
function focusPageSearch() {
  const focusIt = (el) => {
    if (!el) return false
    el.focus({ preventScroll: true })
    el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    el.classList.add('search-flash')
    window.setTimeout(() => el.classList.remove('search-flash'), 900)
    return true
  }
  if (focusIt(document.querySelector('.page-wrap .search-input'))) return
  if (window.location.hash !== '#/logs') window.location.hash = '#/logs'
  // The Logs page animates in; retry until its search field exists.
  let tries = 0
  const timer = window.setInterval(() => {
    tries += 1
    if (focusIt(document.querySelector('.page-wrap .search-input')) || tries > 10) {
      window.clearInterval(timer)
    }
  }, 250)
}

export function InstitutionalLogos({ className = '' }) {
  // `short` is what renders in the pill (must fit — ~20 chars max);
  // `label` is the full name, kept as the hover tooltip.
  const items = [
    { code: 'DEI', short: 'Entrepreneurship', label: 'Directorate of Entrepreneurship & Innovation' },
    { code: 'SRM', short: 'SRMIST', label: 'SRM Institute of Science and Technology' },
    { code: 'MRC', short: 'Moothstrapper', label: 'Moothstrapper Research Council' },
    { code: 'BIRAC', short: 'BioNEST · SRM', label: 'Birac BioNEST — SRM MCH' },
  ]
  return (
    <div className={`institutional-strip ${className}`}>
      {items.map(({ code, short, label }) => (
        <div className="inst-slot" key={code} title={label}>
          <span className="inst-code">{code}</span>
          <span className="inst-tag">{short}</span>
        </div>
      ))}
      <button
        className="inst-slot inst-search"
        type="button"
        title="Search this page"
        aria-label="Search this page"
        onClick={focusPageSearch}
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="11" cy="11" r="7" />
          <line x1="20" y1="20" x2="16.65" y2="16.65" />
        </svg>
      </button>
    </div>
  )
}

/** Wordmark only, for the favicon and tight spots. */
export function FablabCompact({ size = 90, className = '' }) {
  return <FablabMark size={size} className={className} />
}

/**
 * Lab identity block — wordmark + campus subtitle. Shown in the sidebar
 * brand and as the console <title>.
 */
export function LogoLockup({ markSize = 120 }) {
  return (
    <div className="brand-lockup">
      <span className="brand-mark">
        <FablabMark size={markSize} />
      </span>
      <span className="brand-text">
        <span className="brand-inst">FacePass Fab Lab</span>
        <span className="brand-dept">FAB LAB · AAMS</span>
      </span>
    </div>
  )
}

export default FablabMark