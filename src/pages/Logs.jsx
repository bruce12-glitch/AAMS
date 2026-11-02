import { useEffect, useState } from 'react'
import { usePolling } from '../hooks/useApi'
import { toArray } from '../api/client'
import { IS_STATIC_DEMO } from '../config/runtime'
import DataNotice from '../components/DataNotice'
import RecordScope from '../components/RecordScope'
import StatusBadge from '../components/StatusBadge'
import { downloadCsv } from '../utils/download'
import { decisionLabel, resultLabel, sourceLabel, formatEventTime, matchScore, paymentLabel, readableText } from '../utils/records'

export default function Logs() {
  const [scope, setScope] = useState('all')
  const [decision, setDecision] = useState('all')
  const [query, setQuery] = useState('')
  const [term, setTerm] = useState('')
  const [offset, setOffset] = useState(0)
  const limit = 50
  useEffect(() => {
    const timer = setTimeout(() => setTerm(query.trim()), 250)
    return () => clearTimeout(timer)
  }, [query])
  const params = new URLSearchParams({ limit, offset, scope, decision, q: term })
  const { data, loading, error, refresh } = usePolling(`/dashboard/activity?${params}`, { activities: [] }, 8000, { enabled: !IS_STATIC_DEMO })
  const current = data?.scope === scope && data?.q === query.trim() && data?.decision === decision && data?.offset === offset
  const rows = current ? toArray(data, 'activities') : []
  const total = current ? data.total : 0
  const waiting = !IS_STATIC_DEMO && (loading || (!current && !error))
  const changeScope = (value) => { setOffset(0); setScope(value) }
  const exportRows = () => downloadCsv('aams-entry-logs.csv', [
    ['Time', 'Matched name', 'Matched ID', 'Claimed ID', 'Decision', 'Reason', 'Source', 'Comparison performed', 'Similarity', 'Payment'],
    ...rows.map((row) => [row.event_time, row.recognized_name, row.recognized_id, row.claimed_id, decisionLabel(row.decision), readableText(row.reason), sourceLabel(row.event_source), row.comparison_performed ?? '', matchScore(row), paymentLabel(row.payment_status)]),
  ])
  return (
    <div className="page-wrap records-surface">
      <div className="records-page-head">
        <div><h1 className="page-title">Entry Logs</h1><p className="page-sub">Search saved decisions across the database. Demo examples and older records remain labelled. A denied attempt is not attendance.</p></div>
        <div className="action-row"><button className="btn ghost" type="button" onClick={exportRows} disabled={!rows.length}>Export CSV</button>
          <button className="btn ghost" type="button" onClick={refresh}>Refresh</button></div>
      </div>
      <DataNotice error={error} loading={loading} />
      <section className="panel records-panel" aria-label="Access decision records">
        <RecordScope scope={scope} onChange={changeScope} counts={data?.source_counts} />
        <div className="records-toolbar">
          <label>Decision<select aria-label="Decision" value={decision} onChange={(event) => { setOffset(0); setDecision(event.target.value) }}>
            <option value="all">All decisions</option><option value="GRANTED">Granted</option><option value="DENIED">Denied</option>
          </select></label>
          <label className="record-search">Search records<input aria-label="Search records" value={query} onChange={(event) => { setOffset(0); setQuery(event.target.value) }} placeholder="Name, student ID or reason — all saved records" maxLength={200} /></label>
          <span className="event-meta" role="status">{waiting ? 'Searching…' : `${total ? offset + 1 : 0}–${offset + rows.length} of ${total} matching records`}</span>
        </div>
        <div className="records-table-scroll" tabIndex={0} aria-label="Entry log table, scroll horizontally on small screens">
          <table className="data-table ops-table">
            <thead><tr><th>Time (IST)</th><th>Person</th><th>Decision & reason</th><th>Face match</th><th>Payment</th><th>Source</th></tr></thead>
            <tbody>{rows.map((row) => <tr key={row.id}>
              <td><time>{formatEventTime(row.event_time)}</time><small>Attempt #{row.id}</small></td>
              <td><strong>{row.recognized_name || row.recognized_id || 'Not identified'}</strong>
                {row.recognized_name && <small>{row.recognized_id}</small>}
                {row.claimed_id && row.claimed_id !== row.recognized_id && <small>Pass: {row.claimed_name || row.claimed_id}</small>}</td>
              <td><StatusBadge value={row.decision} label={decisionLabel(row.decision)} />
                <p className="event-reason">{readableText(row.reason) || resultLabel(row.tag)}</p></td>
              <td>{matchScore(row)}</td><td>{paymentLabel(row.payment_status)}</td><td>{sourceLabel(row.event_source)}</td>
            </tr>)}</tbody>
          </table>
        </div>
        {!rows.length && <div className="records-empty">
          <p>{waiting ? 'Searching saved access decisions…' : error ? 'Records could not be loaded. Use Refresh to retry.' : query.trim() ? `No records match “${query.trim()}” in this scope.` : 'No access decisions in this view. A photo check does not save attendance; use Record entry or webcam attendance.'}</p>
          {!waiting && !error && <button className="btn ghost" type="button" onClick={() => { setQuery(''); setTerm(''); setDecision('all'); changeScope('all') }}>Show all records</button>}
        </div>}
        <div className="action-row" aria-label="Record pages">
          <button className="btn ghost" type="button" disabled={waiting || offset === 0} onClick={() => setOffset(Math.max(0, offset - limit))}>Previous records</button>
          <button className="btn ghost" type="button" disabled={waiting || offset + limit >= total} onClick={() => setOffset(offset + limit)}>Next records</button>
          <small>CSV exports the displayed page.</small>
        </div>
      </section>
    </div>
  )
}
