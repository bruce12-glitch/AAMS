import { motion } from 'framer-motion'
import { usePolling } from '../hooks/useApi'
import { IS_STATIC_DEMO } from '../config/runtime'
import { MOCK_DAILY_REPORT, MOCK_STATS } from '../api/mock'

function ReportCard({ title, rows, delay = 0, footer }) {
  return (
    <motion.section
      className="panel hoverable"
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, delay }}
    >
      <div className="panel-head">
        <h2 className="panel-title"><span className="tick" />{title}</h2>
        {footer && <span className="panel-link">{footer}</span>}
      </div>
      {rows.length === 0 && (
        <div className="empty-state">No data yet.<span className="mono">—</span></div>
      )}
      {rows.map(([k, v]) => (
        <div className="kv-row" key={k}>
          <span className="kv-key">{k.replace(/_/g, ' ')}</span>
          <span className="kv-val">{String(v ?? '—')}</span>
        </div>
      ))}
    </motion.section>
  )
}

const pick = (obj, keys) => keys.filter((k) => obj && k in obj).map((k) => [k, obj[k]])

// Stable fallback identities. These were previously inline literals inside the
// component, which meant a brand-new object every render.
const EMPTY_WEEK = { week: '(demo)' }
const EMPTY_LIST = []
const EMPTY_OBJ = {}

const listRows = (payload) => {
  const arr = Array.isArray(payload) ? payload : (payload?.attempts ?? payload?.rows ?? [])
  if (!Array.isArray(arr)) return []
  return arr.slice(0, 8).map((a, i) => [
    a.event_time || a.date || `#${i + 1}`,
    [a.name, a.claimed_id, a.tag].filter(Boolean).join(' · ') || 'event'
  ])
}

export default function Reports() {
  // Reports reads six endpoints. All fallbacks are now module-level constants
  // with stable identity, so the fallbackRef in usePolling never sees a new
  // object on every render.
  const LIVE = { enabled: !IS_STATIC_DEMO }
  const stats = usePolling('/dashboard/stats', MOCK_STATS, 8000, LIVE)
  const daily = usePolling('/reports/daily', MOCK_DAILY_REPORT, 8000, LIVE)
  const weekly = usePolling('/reports/weekly', EMPTY_WEEK, 8000, LIVE)
  const proxy = usePolling('/reports/proxy', EMPTY_LIST, 8000, LIVE)
  const unpaid = usePolling('/reports/unpaid', EMPTY_LIST, 8000, LIVE)
  const occ = usePolling('/reports/occupancy', EMPTY_OBJ, 8000, LIVE)

  const s = stats.data ?? {}
  const d = daily.data ?? {}

  const dailyKeys = ['date', 'total_entries', 'unique_users', 'authorized_entries',
    'granted', 'denied']
  const secKeys = ['proxy_attempts', 'unpaid_attempts', 'unknown_attempts',
    'spoof_attempts', 'tailgate_alerts']

  return (
    <div className="page-wrap">
      <div className="page-intro">
        <h1 className="page-title">Reports</h1>
        <p className="page-sub">Live summaries from the reporting engine — also delivered to the in-charge at 20:00 via Telegram.</p>
      </div>

      <div className="report-grid">
        <ReportCard title="Daily Summary" delay={0}
          rows={pick(d, dailyKeys).length ? pick(d, dailyKeys) : pick(MOCK_DAILY_REPORT, dailyKeys)}
          footer={daily.isLive ? 'live' : 'demo'} />

        <ReportCard title="Security Events" delay={0.08}
          rows={[...pick(d, secKeys),
            ...listRows(proxy.data).slice(0, 3).map(([t, v]) => [`proxy @ ${t}`, v]),
            ...listRows(unpaid.data).slice(0, 3).map(([t, v]) => [`unpaid @ ${t}`, v])]}
          footer={`${(proxy.isLive && unpaid.isLive) ? 'live' : 'demo'}`} />

        <ReportCard title="Right Now" delay={0.16}
          rows={[
            ['Inside lab', s.inside_count ?? 0],
            ['Open alerts', s.alert_count ?? 0],
            ['Paid members', s.member_count ?? 0],
            ['Entries today', s.total_entries ?? 0]
          ]} />

        <ReportCard title="Occupancy Report" delay={0.24}
          rows={(() => {
            const o = occ.data ?? {}
            const rows = pick(o, ['peak_occupancy', 'current_occupancy',
              'total_entries_today', 'timeout_exits', 'avg_duration_minutes'])
            if (rows.length) return rows
            const arr = Array.isArray(o) ? o.slice(0, 6) : []
            return arr.map((r, i) => [r.entry_time?.slice(11, 16) ?? `#${i + 1}`,
              `${r.user_id} · ${r.status}`])
          })()} />

        <ReportCard title="Weekly Trend" delay={0.32}
          rows={(() => {
            const w = weekly.data ?? {}
            const rows = pick(w, ['week_start', 'week_end', 'total_entries',
              'unique_users', 'proxy_attempts', 'unpaid_attempts'])
            if (rows.length) return rows
            return [['week', '(demo data — backend offline)']]
          })()}
          footer={weekly.isLive ? 'live' : 'demo'} />

        <ReportCard title="Retention Policy (§26)" delay={0.4}
          rows={[
            ['Entry logs', 'purged after 90 days'],
            ['Alert images', 'purged after 30 days'],
            ['Daily reports', 'kept 1 year']
          ]} />
      </div>
    </div>
  )
}
