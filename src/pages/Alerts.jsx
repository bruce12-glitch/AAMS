import { useState } from 'react'
import { usePolling } from '../hooks/useApi'
import { toArray, adminPost } from '../api/client'
import { IS_STATIC_DEMO } from '../config/runtime'
import { useAuth } from '../auth/AuthContext'
import DataNotice from '../components/DataNotice'
import RecordScope from '../components/RecordScope'
import AlertList from '../components/AlertList'

export default function Alerts() {
  const [scope, setScope] = useState('recorded')
  const [review, setReview] = useState('open')
  const [priority, setPriority] = useState('all')
  const [busyId, setBusyId] = useState(null)
  const [actionError, setActionError] = useState('')
  const [success, setSuccess] = useState('')
  const { isAdmin } = useAuth()
  const { data, error, loading, refresh } = usePolling(`/alerts?scope=${scope}&status=${review}`, { alerts: [] }, 8000, { enabled: !IS_STATIC_DEMO })
  const list = data?.scope === scope ? toArray(data, 'alerts').filter((row) =>
    (priority === 'all' || row.severity === priority) && (review === 'all' || Boolean(row.acked) === (review === 'reviewed'))) : []
  const markReviewed = async (id) => {
    setBusyId(id); setActionError(''); setSuccess('')
    try { await adminPost(`/alerts/${id}/ack`); await refresh(); setSuccess(`Review #${id} marked reviewed.`) }
    catch (err) { setActionError(err.message || 'Could not save review status.') }
    finally { setBusyId(null) }
  }
  return (
    <div className="page-wrap records-surface">
      <div className="records-page-head">
        <div><h1 className="page-title">Security Alerts</h1><p className="page-sub">Access decisions that need review—not proof of misconduct.</p></div>
        <button className="btn ghost" type="button" onClick={refresh}>Refresh</button>
      </div>
      <DataNotice error={error || actionError} loading={loading} />
      {success && <p className="success-note" role="status">{success}</p>}
      <section className="panel records-panel" aria-label="Security review queue">
        <RecordScope scope={scope} onChange={setScope} counts={data?.source_counts} />
        <div className="records-toolbar">
          <label>Review status<select value={review} onChange={(event) => setReview(event.target.value)}><option value="open">Needs review</option><option value="reviewed">Reviewed</option><option value="all">All review states</option></select></label>
          <label>Priority<select value={priority} onChange={(event) => setPriority(event.target.value)}><option value="all">All priorities</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select></label>
          <span className="event-meta">{list.length} shown · latest 100</span>
        </div>
        {!isAdmin && <p className="read-only-note">Read-only member view. An administrator can mark an item reviewed.</p>}
        <AlertList items={list} busyId={busyId} onReview={isAdmin && !IS_STATIC_DEMO ? markReviewed : undefined} />
        {!list.length && <p className="records-empty">{loading ? 'Loading review items…' : error ? 'Review records are unavailable. Refresh to retry.' : 'No review items in this view. Older and demo records remain in history.'}</p>}
      </section>
    </div>
  )
}
