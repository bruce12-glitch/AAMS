const KNOWN = new Set([
  'granted', 'authorized', 'active', 'inside',
  'denied', 'proxy', 'spoof', 'expired',
  'unpaid', 'unknown', 'tailgate',
  'noface'
])

export default function StatusBadge({ value, label }) {
  const v = String(value ?? 'not recorded').toLowerCase()
  const cls = KNOWN.has(v) ? v : 'neutral'
  return (
    <span
      className={`badge ${cls}`}
    >
      <span className="badge-dot" />
      {label ?? v.replace(/_/g, ' ')}
    </span>
  )
}
