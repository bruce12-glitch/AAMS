import { parseTimestamp, LAB_TIME_ZONE } from '../utils/time'
import { useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { usePolling } from '../hooks/useApi'
import { toArray } from '../api/client'
import { IS_STATIC_DEMO } from '../config/runtime'
import { MOCK_ACTIVITY } from '../api/mock'
import DataNotice from '../components/DataNotice'
import { downloadCsv } from '../utils/download'
import StatusBadge from '../components/StatusBadge'

const TAGS = ['all', 'authorized', 'proxy', 'unpaid', 'unknown', 'spoof', 'tailgate']

// See Dashboard.jsx: isNaN(d) is unreliable on Date objects. Use getTime().
const fmt = (iso) => {
  const d = parseTimestamp(iso)
  return Number.isNaN(d.getTime())
    ? '—'
    : d.toLocaleString('en-IN', { timeZone: LAB_TIME_ZONE, day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
}

export default function Logs() {
  const { data, isLive, loading, error, refresh } = usePolling(
    '/dashboard/activity?limit=500',
    MOCK_ACTIVITY,
    8000,
    { enabled: !IS_STATIC_DEMO }
  )
  const [filter, setFilter] = useState('all')
  const [query, setQuery] = useState('')

  const rows = useMemo(() => {
    let list = toArray(data, 'activities')
    if (filter !== 'all') list = list.filter((r) => String(r.tag ?? '').toLowerCase() === filter)
    if (query.trim()) {
      const q = query.trim().toLowerCase()
      list = list.filter((r) =>
        [r.claimed_id, r.recognized_id, r.tag, r.decision]
          .some((f) => String(f ?? '').toLowerCase().includes(q))
      )
    }
    return list
  }, [data, filter, query])

  return (
    <div className="page-wrap">
      <div className="page-intro" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', gap: 16 }}>
        <div>
          <h1 className="page-title">Entry Logs</h1>
          <p className="page-sub">Latest 500 access attempts with identity, face similarity and decision. Export the filtered records as CSV.</p>
        </div>
        <div className="action-row"><button className="btn sm ghost" type="button" disabled={!rows.length} onClick={() => downloadCsv('aams-entry-logs.csv', [['Time', 'Claimed ID', 'Recognized ID', 'Similarity', 'Decision', 'Reason'], ...rows.map((row) => [row.event_time, row.claimed_id, row.recognized_id, row.similarity, row.decision, row.reason])])}>Export CSV</button><button className="btn sm ghost" onClick={refresh} type="button">↻ Refresh</button></div>
      </div>

      <DataNotice error={error} loading={loading} />
      <motion.div
        className="panel table-panel"
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45 }}
        style={{ position: 'relative' }}
      >
        {loading && <span className="loading-bar" />}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, marginBottom: 16 }}>
          <div className="chip-row">
            {TAGS.map((t) => (
              <button
                key={t}
                className={`filter-chip ${filter === t ? 'on' : ''}`}
                onClick={() => setFilter(t)}
                type="button"
              >
                {t}
              </button>
            ))}
          </div>
          <input
            className="search-input"
            style={{ marginLeft: 'auto' }}
            placeholder="Search ID / status…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>

        <table className="data-table">
          <thead>
            <tr>
              <th>Time</th><th>Claimed ID</th><th>Recognized</th><th>Sim</th><th>Payment</th><th>Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <motion.tr
                key={r.id ?? i}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: Math.min(i * 0.035, 0.4) }}
              >
                <td className="mono">{fmt(r.event_time)}</td>
                <td className="mono name-cell">{r.claimed_id || '—'}</td>
                <td className="mono">{r.recognized_id || '—'}</td>
                <td className="mono">{typeof r.similarity === 'number' ? r.similarity.toFixed(2) : '—'}</td>
                <td><StatusBadge value={r.payment_status} /></td>
                <td><StatusBadge value={r.tag || r.decision} /></td>
              </motion.tr>
            ))}
            {rows.length === 0 && !loading && (
              <tr><td colSpan={6}><div className="empty-state">No matching entries.<span className="mono">TRY CLEARING FILTERS</span></div></td></tr>
            )}
          </tbody>
        </table>

        {!isLive && (
          <p className="alert-time" style={{ marginTop: 12 }}>Backend unavailable. Previously loaded records may be out of date.</p>
        )}
      </motion.div>
    </div>
  )
}
