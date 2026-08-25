import { motion } from 'framer-motion'
import { usePolling } from '../hooks/useApi'
import { MOCK_DAILY_REPORT, MOCK_STATS } from '../api/mock'

function ReportCard({ title, rows, delay = 0 }) {
  return (
    <motion.section
      className="panel hoverable"
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, delay }}
    >
      <div className="panel-head">
        <h2 className="panel-title"><span className="tick" />{title}</h2>
      </div>
      {rows.map(([k, v]) => (
        <div className="kv-row" key={k}>
          <span className="kv-key">{k}</span>
          <span className="kv-val">{v}</span>
        </div>
      ))}
    </motion.section>
  )
}

export default function Reports() {
  const stats = usePolling('/dashboard/stats', MOCK_STATS)
  const s = stats.data ?? MOCK_STATS
  const r = MOCK_DAILY_REPORT

  return (
    <div className="page-wrap">
      <div className="page-intro">
        <h1 className="page-title">Reports</h1>
        <p className="page-sub">Daily summary delivered to the in-charge at 20:00 via Telegram (§15.2).</p>
      </div>

      <div className="report-grid">
        <ReportCard
          title={`Daily Summary — ${r.date}`}
          delay={0}
          rows={[
            ['Total entries', r.total_entries],
            ['Unique users', r.unique_users],
            ['Authorized', r.authorized]
          ]}
        />
        <ReportCard
          title="Security Events"
          delay={0.08}
          rows={[
            ['Proxy attempts', r.proxy_attempts],
            ['Unpaid attempts', r.unpaid_attempts],
            ['Unknown persons', r.unknown_attempts]
          ]}
        />
        <ReportCard
          title="Right Now"
          delay={0.16}
          rows={[
            ['Inside lab', s.inside_count ?? 0],
            ['Open alerts', s.alert_count ?? 0],
            ['Paid members', s.member_count ?? 0]
          ]}
        />
        <ReportCard
          title="Retention Policy (§26)"
          delay={0.24}
          rows={[
            ['Entry logs', '90 days'],
            ['Alert images', '30 days'],
            ['Daily reports', '1 year']
          ]}
        />
      </div>
    </div>
  )
}
