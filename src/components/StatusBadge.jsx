import { motion } from 'framer-motion'

const KNOWN = new Set([
  'granted', 'authorized', 'active', 'inside',
  'denied', 'proxy', 'spoof', 'expired',
  'unpaid', 'unknown', 'tailgate',
  'noface'
])

export default function StatusBadge({ value }) {
  const v = String(value ?? 'neutral').toLowerCase()
  const cls = KNOWN.has(v) ? v : 'neutral'
  return (
    <motion.span
      className={`badge ${cls}`}
      initial={{ opacity: 0, scale: 0.85 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.25 }}
    >
      <span className="badge-dot" />
      {v.replace(/_/g, ' ')}
    </motion.span>
  )
}
