import { useState } from 'react'
import { adminPost } from '../api/client'
import { usePolling } from '../hooks/useApi'

const EMPTY = {}
const MODEL_LABELS = { not_loaded: 'Setup needed', loading: 'Downloading / loading…', ready: 'Ready', failed: 'Could not load — retry' }

export default function PrototypeSetup({ onNavigate }) {
  const status = usePolling('/admin/readiness', EMPTY, 4000)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const s = status.data ?? EMPTY
  const recognitionReady = status.isLive && s.cv_engine === 'ready' && s.eligible_members > 0
  const initialize = async () => {
    setBusy(true); setError(''); setMessage('')
    try {
      const response = await adminPost('/admin/vision/warmup', {})
      setMessage(response.message || 'Face model is ready.')
      status.refresh()
    } catch (err) { setError(err.message) }
    finally { setBusy(false) }
  }
  return <section className="panel prototype-setup" aria-label="Prototype setup">
    <div className="panel-head"><h2 className="panel-title">Prototype setup</h2><span className={`badge ${recognitionReady ? 'active' : 'pending'}`}>{recognitionReady ? 'Ready for camera rehearsal' : status.isLive ? 'Finish setup below' : 'Checking connection'}</span></div>
    <ol className="setup-checks">
      <li><strong>Database</strong><span>{s.database === 'ready' ? 'Connected · records persist locally' : 'Checking…'}</span></li>
      <li><strong>Face model</strong><span>{MODEL_LABELS[s.cv_engine] || 'Checking…'}</span></li>
      <li><strong>Members</strong><span>{s.enrolled_members ?? '—'} enrolled / {s.active_members ?? '—'} active</span></li>
      <li><strong>Entry eligibility</strong><span>{s.eligible_members ?? '—'} enrolled with current active payment</span></li>
      <li><strong>Telegram</strong><span>{!s.telegram?.configured ? 'Connect a personal chat or group' : !s.telegram.notify_on_entry ? 'Automatic entry messages are off' : s.telegram.last_sent_at ? 'Delivery recorded · confirm receipt on phone' : 'Configured · send a test to confirm'}</span><span>{s.telegram?.pending_count ?? 0} messages awaiting delivery</span></li>
    </ol>
    <p className="field-hint">Initialize the model before enrolling faces. The first download needs internet and may take several minutes; later starts reuse the saved models. Register consenting members with active payment, then start webcam attendance in Live Monitor.</p>
    <p className="field-hint">Demo rehearsal: recognize one member → check their name and Telegram delivery status → scan again to show duplicate prevention → check out on Dashboard → demonstrate re-entry. Local recognition works offline after model setup; Telegram needs internet.</p>
    {(error || status.error || s.cv_engine === 'failed') && <div className="form-error" role="alert">{error || status.error || 'Face model could not load. Check internet, disk space and the model cache, then retry.'}</div>}
    {message && s.cv_engine !== 'failed' && <p className="field-hint" role="status">{s.cv_engine === 'ready' ? 'Face model is ready for enrollment and attendance.' : message}</p>}
    <div className="action-row">
      <button className="btn primary" type="button" disabled={busy || !status.isLive || ['loading', 'ready'].includes(s.cv_engine)} onClick={initialize}>{s.cv_engine === 'failed' ? 'Retry face model' : s.cv_engine === 'loading' ? 'Loading face model…' : 'Initialize face model'}</button>
      <button className="btn ghost" type="button" onClick={() => onNavigate('users')}>Register members</button>
      <button className="btn ghost" type="button" onClick={() => onNavigate('communicate')}>Connect Telegram</button>
      <button className="btn ghost" type="button" onClick={() => onNavigate('live')}>Open webcam attendance</button>
    </div>
  </section>
}
