import { motion } from 'framer-motion'
import { useCountUp } from '../hooks/useCountUp'

export default function StatCard({ label, value, icon, color = '#22d3ee', tint = 'rgba(34,211,238,0.12)', trend, trendDir = 'flat', index = 0 }) {
  const shown = useCountUp(Number.isFinite(value) ? value : 0)

  return (
    <motion.div
      className="panel stat-card hoverable"
      style={{ '--stat-color': color, '--stat-tint': tint }}
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, delay: index * 0.08, ease: [0.22, 1, 0.36, 1] }}
    >
      <div className="stat-top">
        <span className="stat-label">{label}</span>
        <span className="stat-icon">{icon}</span>
      </div>
      <div className="stat-value">{shown.toLocaleString('en-IN')}</div>
      <div className="stat-foot">
        {trend && (
          <span className={`trend-chip ${trendDir}`}>
            {trendDir === 'down' ? '▼' : trendDir === 'up' ? '▲' : '■'} {trend}
          </span>
        )}
        <span>vs yesterday</span>
      </div>
    </motion.div>
  )
}
