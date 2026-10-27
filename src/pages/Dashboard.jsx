import { useState } from 'react'
import { useAuth } from '../auth/AuthContext'
import { adminPost, toArray } from '../api/client'
import { usePolling } from '../hooks/useApi'
import { IS_STATIC_DEMO } from '../config/runtime'
import DataNotice from '../components/DataNotice'
import StatCard from '../components/StatCard'
import PrototypeSetup from '../components/PrototypeSetup'
import StatusBadge from '../components/StatusBadge'
import AlertList from '../components/AlertList'
import { formatEventTime, decisionLabel, readableText, sourceLabel, historyCount } from '../utils/records'
import { IconDoor, IconFace, IconBell, IconUsers } from '../components/icons'

const LIVE = { enabled: !IS_STATIC_DEMO }

export default function Dashboard({ onNavigate }) {
  const stats = usePolling('/dashboard/stats?scope=recorded', null, 8000, LIVE)
  const activity = usePolling('/dashboard/activity?scope=recorded', { activities: [] }, 8000, LIVE)
  const alerts = usePolling('/alerts?scope=recorded&status=open', { alerts: [] }, 8000, LIVE)
  const occupants = usePolling('/occupants', { occupants: [] }, 8000, LIVE)
  const { isAdmin } = useAuth()
  const [exitError, setExitError] = useState('')
  const [exiting, setExiting] = useState(null)
  const checkout = async (id) => {
    setExiting(id); setExitError('')
    try { await adminPost(`/occupants/${encodeURIComponent(id)}/exit`, {}); await occupants.refresh(); stats.refresh() }
    catch (err) { setExitError(err.message) }
    finally { setExiting(null) }
  }
  const s = stats.data || {}
  const acts = toArray(activity.data, 'activities').slice(0, 8)
  const alertList = toArray(alerts.data, 'alerts').slice(0, 5)
  const occList = toArray(occupants.data, 'occupants').filter((row) => row.status === 'inside')
  const trend = stats.isLive ? 'recorded' : 'unavailable'
  return (
    <div className="page-wrap records-surface">
      <div className="page-intro"><h1 className="page-title">Mission Overview</h1><p className="page-sub">Recorded access decisions, open visits and items needing review.</p></div>
      <DataNotice error={exitError || stats.error || activity.error || alerts.error || occupants.error} loading={stats.loading} />
      {isAdmin && !IS_STATIC_DEMO && <PrototypeSetup onNavigate={onNavigate} />}
      <div className="grid-stats">
        <StatCard index={0} label="Granted Entries Today" value={s.total_entries} icon={<IconDoor width={17} />} color="#0e7490" tint="#ecfeff" trend={trend} trendDir="flat" />
        <StatCard index={1} label="Open Visits" value={s.inside_count} icon={<IconFace width={17} />} color="#047857" tint="#ecfdf5" trend={trend} trendDir="flat" />
        <StatCard index={2} label="Needs Review" value={s.alert_count} icon={<IconBell width={17} />} color="#b91c1c" tint="#fef2f2" trend={trend} trendDir="flat" />
        <StatCard index={3} label="Paid Members" value={s.member_count} icon={<IconUsers width={17} />} color="#6d28d9" tint="#f5f3ff" trend={trend} trendDir="flat" />
      </div>
      <div className="grid-main">
        <section className="panel records-panel" aria-label="Recent access decisions">
          <div className="panel-head"><h2 className="panel-title">Recent access decisions</h2><button className="panel-link" type="button" onClick={() => onNavigate('logs')}>Entry Logs →</button></div>
          <div className="records-table-scroll" tabIndex={0} aria-label="Recent access decisions table">
            <table className="data-table ops-table">
              <thead><tr><th>Time (IST)</th><th>Person</th><th>Decision</th><th>Reason</th></tr></thead>
              <tbody>{acts.map((row) => <tr key={row.id}>
                <td>{formatEventTime(row.event_time)}</td>
                <td><strong>{row.recognized_name || row.recognized_id || 'Not identified'}</strong><small>{sourceLabel(row.event_source)}</small></td>
                <td><StatusBadge value={row.decision} label={decisionLabel(row.decision)} /></td>
                <td>{readableText(row.reason) || 'Not recorded'}</td>
              </tr>)}</tbody>
            </table>
          </div>
          {!acts.length && <p className="records-empty">{activity.loading ? 'Loading access decisions…' : activity.error || IS_STATIC_DEMO ? 'No live access records available.' : 'No access decisions recorded in the current capture history.'}</p>}
          <p className="event-meta">{historyCount(activity.data?.source_counts)} older or demo records are preserved in Entry Logs history. Denied attempts are not counted as attendance.</p>
        </section>
        <div className="stack">
          <section className="panel records-panel" aria-label="Open visits">
            <div className="panel-head"><h2 className="panel-title">Open visits</h2><span className="event-meta">{occList.length} recorded</span></div>
            {!occList.length && <p className="records-empty">{occupants.error || IS_STATIC_DEMO ? 'Visit records are unavailable.' : occupants.loading ? 'Loading visits…' : 'No open visits recorded.'}</p>}
            {occList.slice(0, 6).map((row) => <div className="event-row" key={row.user_id}>
              <div className="event-row-main"><strong>{row.name || row.user_id}</strong><p className="event-meta">{row.user_id} · {formatEventTime(row.entry_time)}</p></div>
              {isAdmin && <button className="btn sm ghost" type="button" disabled={exiting === row.user_id} onClick={() => checkout(row.user_id)}>Check out</button>}
            </div>)}
          </section>
          <section className="panel records-panel" aria-label="Recent security reviews">
            <div className="panel-head"><h2 className="panel-title">Needs review</h2><button className="panel-link" type="button" onClick={() => onNavigate('alerts')}>View queue →</button></div>
            <AlertList items={alertList} compact />
            {!alertList.length && <p className="records-empty">{alerts.error || IS_STATIC_DEMO ? 'Review records are unavailable.' : alerts.loading ? 'Loading reviews…' : 'No open review items for current recorded events.'}</p>}
            <p className="event-meta">{historyCount(alerts.data?.source_counts)} older or demo alerts kept in history. A review item is not proof of misconduct.</p>
          </section>
        </div>
      </div>
    </div>
  )
}
