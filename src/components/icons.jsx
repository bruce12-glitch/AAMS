const base = {
  width: 16,
  height: 16,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.8,
  strokeLinecap: 'round',
  strokeLinejoin: 'round'
}

export const IconGauge = (p) => (
  <svg {...base} {...p}>
    <path d="M12 4a8 8 0 0 0-8 8c0 1.6.5 3.1 1.2 4.4L12 12" />
    <path d="M12 4a8 8 0 0 1 8 8c0 1.6-.5 3.1-1.2 4.4L12 12" />
    <circle cx="12" cy="12" r="1.6" />
    <path d="M5 20h14" />
  </svg>
)

export const IconScan = (p) => (
  <svg {...base} {...p}>
    <path d="M3 7V5a2 2 0 0 1 2-2h2" />
    <path d="M17 3h2a2 2 0 0 1 2 2v2" />
    <path d="M21 17v2a2 2 0 0 1-2 2h-2" />
    <path d="M7 21H5a2 2 0 0 1-2-2v-2" />
    <line x1="7" y1="12" x2="17" y2="12" />
  </svg>
)

export const IconList = (p) => (
  <svg {...base} {...p}>
    <line x1="8" y1="6" x2="20" y2="6" />
    <line x1="8" y1="12" x2="20" y2="12" />
    <line x1="8" y1="18" x2="20" y2="18" />
    <circle cx="4" cy="6" r="0.6" fill="currentColor" />
    <circle cx="4" cy="12" r="0.6" fill="currentColor" />
    <circle cx="4" cy="18" r="0.6" fill="currentColor" />
  </svg>
)

export const IconBell = (p) => (
  <svg {...base} {...p}>
    <path d="M18 9a6 6 0 1 0-12 0c0 6-2.5 7-2.5 7h17S18 15 18 9" />
    <path d="M10 20a2.2 2.2 0 0 0 4 0" />
  </svg>
)

export const IconUsers = (p) => (
  <svg {...base} {...p}>
    <circle cx="9" cy="8" r="3.2" />
    <path d="M3.5 19c.6-3 2.9-4.6 5.5-4.6s4.9 1.6 5.5 4.6" />
    <circle cx="17" cy="9" r="2.4" />
    <path d="M16 14.7c2 .2 3.8 1.5 4.4 4.3" />
  </svg>
)

export const IconReport = (p) => (
  <svg {...base} {...p}>
    <rect x="5" y="3" width="14" height="18" rx="2" />
    <line x1="9" y1="8" x2="15" y2="8" />
    <line x1="9" y1="12" x2="15" y2="12" />
    <line x1="9" y1="16" x2="13" y2="16" />
  </svg>
)

export const IconCheck = (p) => (
  <svg {...base} {...p}>
    <path d="M4 12.5l5 5L20 6.5" />
  </svg>
)

export const IconX = (p) => (
  <svg {...base} {...p}>
    <line x1="6" y1="6" x2="18" y2="18" />
    <line x1="18" y1="6" x2="6" y2="18" />
  </svg>
)

export const IconDoor = (p) => (
  <svg {...base} {...p}>
    <path d="M13 3H5a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h8" />
    <path d="M13 3l6 2v14l-6 2" />
    <circle cx="10.4" cy="12" r="0.8" fill="currentColor" stroke="none" />
  </svg>
)

export const IconFace = (p) => (
  <svg {...base} {...p}>
    <circle cx="12" cy="11" r="6.5" />
    <circle cx="9.6" cy="10" r="0.5" fill="currentColor" />
    <circle cx="14.4" cy="10" r="0.5" fill="currentColor" />
    <path d="M9.5 13.5c.7.8 1.6 1.2 2.5 1.2s1.8-.4 2.5-1.2" />
    <path d="M4 21c1.8-2.2 4.7-3.5 8-3.5s6.2 1.3 8 3.5" />
  </svg>
)
