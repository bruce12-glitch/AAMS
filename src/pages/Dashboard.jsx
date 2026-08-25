import { motion } from 'framer-motion'
import { usePolling } from '../hooks/useApi'
import { toArray } from '../api/client'
import { MOCK_STATS, MOCK_ACTIVITY, MOCK_ALERTS, MOCK_OCCUPANTS } from '../api/mock'
import StatCard from '../components/StatCard'
import StatusBadge from '../components/StatusBadge'
import { IconDoor, IconFace, IconBell, IconUsers } from '../components/icons'

const fmtTime = (iso) => {
  const d = new Date(iso)
  return isNaN(d) ? '—' : d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })
}

const initials = (id) => (id ? id.replace(/[^a-z]/gi, '').slice(0, 2).toUpperCase() : '??')

export default function Dashboard({ onNavigate }) {
  const stats = usePolling('/dashboard/stats', MOCK_STATS)
  const activity = usePolling('/dashboard/activity', { activities: MOCK_ACTIVITY })
  const alerts = usePolling('/alerts', { alerts: MOCK_ALERTS })
  const occupants = usePolling('/occupants', { occupants: MOCK_OCCUPANTS })

  const s = stats.data ?? MOCK_STATS
  const acts = toArray(activity.data, 'activities').slice(0, 8)
  const alertList = toArray(alerts.data, 'alerts').slice(0, 5)
  const occList = toArray(occupants.data, 'occupants').filter((o) => o.status === 'inside')

  return (
    <div className="page-wrap">
      <div className="page-intro">
        <h1 className="page-title">Mission Overview</h1>
        <p className="page-sub">Real-time Fab Lab access control — entries, occupancy and security events.</p>
      </div>

      <div className="grid-stats">
        <StatCard index={0} label="Entries Today" value={s.total_entries} icon={<IconDoor width={17} height={17} />} color="#22d3ee" tint="rgba(34,211,238,.12)" trend="+12%" trendDir="up" />
        <StatCard index={1} label="Inside Now" value={s.inside_count} icon={<IconFace width={17} height={17} />} color="#34d399" tint="rgba(52,211,153,.12)" trend="live" trendDir="flat" />
        <StatCard index={2} label="Open Alerts" value={s.alert_count} icon={<IconBell width={17} height={17} />} color="#f87171" tint="rgba(248,113,113,.12)" trend="-2" trendDir="down" />
        <StatCard index={3} label="Paid Members" value={s.member_count} icon={<IconUsers width={17} height={17} />} color="#a78bfa" tint="rgba(167,139,250,.12)" trend="+3" trendDir="up" />
      </div>

      <div className="grid-main">
        <motion.section
          className="panel"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.25 }}
        >
          <div className="panel-head">
            <h2 className="panel-title"><span className="tick" />Recent Activity</h2>
            <button className="panel-link" onClick={() => onNavigate('logs')} type="button">View all →</button>
          </div>
          <table className="data-table">
            <thead>
              <tr>
                <th>Time</th><th>Claimed ID</th><th>Similarity</th><th>Status</th>
              </tr>
            </thead>
            <tbody>
              {acts.map((a, i) => (
                <motion.tr
                  key={a.id ?? i}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.3 + i * 0.05 }}
                >
                  <td className="mono">{fmtTime(a.event_time)}</td>
                  <td className="mono">{a.claimed_id || a.recognized_id || '—'}</td>
                  <td className="mono">{typeof a.similarity === 'number' ? a.similarity.toFixed(2) : '—'}</td>
                  <td><StatusBadge value={a.tag || a.decision} /></td>
                </motion.tr>
              ))}
              {acts.length === 0 && (
                <tr><td colSpan={4}><div className="empty-state">No entries recorded yet.<span className="mono">AWAITING FIRST ENTRY</span></div></td></tr>
              )}
            </tbody>
          </table>
        </motion.section>

        <div className="stack">
          <motion.section
            className="panel"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.35 }}
          >
            <div className="panel-head">
              <h2 className="panel-title"><span className="tick" />Currently Inside</h2>
              <span className="panel-link">{occList.length} present</span>
            </div>
            {occList.length === 0 && (
              <div className="empty-state">Lab is empty right now.<span className="mono">OCCUPANCY 0</span></div>
            )}
            {occList.slice(0, 6).map((o, i) => (
              <div className="occupant-row" key={o.user_id ?? i}>
                <div className={`avatar ${i % 2 ? 'dim' : ''}`}>{initials(o.user_id)}</div>
                <div>
                  <div className="occupant-name mono">{o.user_id}</div>
                  <div className="occupant-meta">In at {fmtTime(o.entry_time)}</div>
                </div>
                <span className="occupant-dur">{Math.round(o.duration_minutes ?? 0)}m</span>
              </div>
            ))}
          </motion.section>

          <motion.section
            className="panel"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.45 }}
          >
            <div className="panel-head">
              <h2 className="panel-title"><span className="tick" />Latest Alerts</h2>
              <button className="panel-link" onClick={() => onNavigate('alerts')} type="button">All alerts →</button>
            </div>
            <div className="stack" style={{ gap: 10 }}>
              {alertList.map((al, i) => (
                <motion.div
                  className={`alert-card ${(al.severity ?? 'low').toLowerCase()}`}
                  key={al.id ?? i}
                  initial={{ opacity: 0, scale: 0.97 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 0.4 + i * 0.06 }}
                >
                  <div style={{ minWidth: 0 }}>
                    <div className="alert-type">{String(al.alert_type ?? 'EVENT').replace(/_/g, ' ')}</div>
                    <div className="alert-msg">{al.message ?? '—'}</div>
                    <div className="alert-time">{fmtTime(al.created_at)}</div>
                  </div>
                </motion.div>
              ))}
              {alertList.length === 0 && <div className="empty-state">All clear.<span className="mono">NO ACTIVE ALERTS</span></div>}
            </div>
          </motion.section>
        </div>
      </div>
    </div>
  )
}
