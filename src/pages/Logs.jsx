import { useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { usePolling } from '../hooks/useApi'
import { toArray } from '../api/client'
import { MOCK_ACTIVITY } from '../api/mock'
import StatusBadge from '../components/StatusBadge'

const TAGS = ['all', 'authorized', 'proxy', 'unpaid', 'unknown', 'spoof', 'tailgate']

const fmt = (iso) => {
  const d = new Date(iso)
  return isNaN(d) ? '—' : d.toLocaleString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
}

export default function Logs() {
  const { data, isLive, loading, refresh } = usePolling('/dashboard/activity', { activities: MOCK_ACTIVITY })
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
          <p className="page-sub">Every access attempt with claimed identity, face similarity and decision.</p>
        </div>
        <button className="btn sm ghost" onClick={refresh} type="button">↻ Refresh</button>
      </div>

      <motion.div
        className="panel"
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
          <p className="alert-time" style={{ marginTop: 12 }}>Backend offline — showing sample trail.</p>
        )}
      </motion.div>
    </div>
  )
}
