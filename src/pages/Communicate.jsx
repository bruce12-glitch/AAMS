import { parseTimestamp, LAB_TIME_ZONE } from '../utils/time'
import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { usePolling } from '../hooks/useApi'
import { adminPost, apiPut, toArray } from '../api/client'
import { IS_STATIC_DEMO } from '../config/runtime'
import { useAuth } from '../auth/AuthContext'
import DataNotice from '../components/DataNotice'

const EMPTY_STATUS = {}
const EMPTY_HISTORY = { notifications: [] }
const DEFAULT_SETTINGS = { enabled: true, bot_token: '', chat_id: '', daily_report_time: '20:00',
  timezone: 'Asia/Kolkata', notify_on_enrollment: true, notify_on_entry: true, send_photo: true }

export default function Communicate() {
  const { isAdmin } = useAuth()
  const status = usePolling('/notify/status', EMPTY_STATUS, 15000, { enabled: !IS_STATIC_DEMO })
  const history = usePolling('/notify/history', EMPTY_HISTORY, 15000, { enabled: !IS_STATIC_DEMO && isAdmin })
  const [settings, setSettings] = useState(DEFAULT_SETTINGS)
  const [dirty, setDirty] = useState(false)
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const s = status.data ?? EMPTY_STATUS
  const ready = Boolean(s.telegram_enabled && s.bot_configured && s.chat_configured)

  useEffect(() => {
    if (!dirty && status.data) {
      const data = status.data
      setSettings((current) => ({ ...current, enabled: Boolean(data.telegram_enabled),
        chat_id: data.chat_id ?? '', daily_report_time: data.daily_report_time ?? '20:00',
        notify_on_entry: data.notify_on_entry ?? true,
        notify_on_enrollment: data.notify_on_enrollment ?? true, send_photo: data.send_photo ?? true }))
    }
  }, [status.data, dirty])

  const set = (key) => (event) => {
    setDirty(true)
    setSettings((current) => ({ ...current, [key]: event.target.type === 'checkbox' ? event.target.checked : event.target.value }))
  }
  const perform = async (action) => {
    if (!isAdmin) return
    setError(''); setResult(null); setBusy(true)
    try {
      const response = await action()
      setResult(response)
      status.refresh(); history.refresh()
      return response
    } catch (err) { setError(err.message || 'Could not complete this action.') }
    finally { setBusy(false) }
  }
  const save = async (event) => {
    event.preventDefault()
    const response = await perform(() => apiPut('/notify/settings', settings))
    if (response?.success) { setSettings((current) => ({ ...current, bot_token: '' })); setDirty(false) }
  }
  const send = async (event) => {
    event.preventDefault()
    const response = await perform(() => adminPost('/notify/send', { message: message.trim() }, 45000))
    if (response?.telegram_sent) setMessage('')
  }
  return (
    <div className="page-wrap">
      <div className="page-intro">
        <h1 className="page-title">Communicate</h1>
        <p className="page-sub">Student updates, entry alerts and a daily summary for your Telegram group.</p>
      </div>
      <DataNotice error={status.error || history.error} loading={status.loading} />
      {error && <div className="form-error" role="alert">{error}</div>}
      {result && <div className={result.telegram_sent === false ? 'form-error' : 'success-note'} role="status">
        {result.telegram_sent === false ? `Saved in the delivery queue: ${result.reason}` : result.reason || result.message || 'Completed.'}
        {result.group_title && <span> Group: {result.group_title}</span>}
      </div>}
      <div className="grid-main">
        <motion.section className="panel" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
          <div className="panel-head"><h2 className="panel-title">Group connection</h2><span className={`badge ${ready ? 'active' : 'pending'}`}>{ready ? 'Configured' : 'Setup needed'}</span></div>
          <div className="kv-row"><span>Daily summary</span><strong>{s.daily_report_time || '20:00'} IST</strong></div>
          <div className="kv-row"><span>Awaiting delivery</span><strong>{s.pending_count ?? '—'}</strong></div>
          <div className="kv-row"><span>Last delivered</span><strong>{s.last_sent_at ? parseTimestamp(s.last_sent_at).toLocaleString('en-IN', { timeZone: LAB_TIME_ZONE }) : 'No delivery yet'}</strong></div>
          {isAdmin ? <form onSubmit={save}>
            <p className="field-hint">Create a bot with Telegram’s BotFather, add it to your group and allow it to post. Save its token and group ID here, verify the group, then send a test.</p>
            <fieldset disabled={busy} className="form-grid">
              <label>Bot token<input type="password" autoComplete="new-password" value={settings.bot_token} onChange={set('bot_token')} placeholder={s.bot_configured ? 'Saved privately · leave blank to keep' : 'Paste bot token'} /></label>
              <label>Group ID<input required value={settings.chat_id} onChange={set('chat_id')} placeholder="-100… or @public_group" /></label>
              <label>Daily report time (IST)<input type="time" required value={settings.daily_report_time} onChange={set('daily_report_time')} /></label>
            </fieldset>
            <label className="consent-row"><input type="checkbox" checked={settings.enabled} onChange={set('enabled')} disabled={busy} />Enable Telegram delivery</label>
            <label className="consent-row"><input type="checkbox" checked={settings.notify_on_enrollment} onChange={set('notify_on_enrollment')} disabled={busy} />Automatically announce student creation and face enrollment</label>
            <label className="consent-row"><input type="checkbox" checked={settings.notify_on_entry} onChange={set('notify_on_entry')} disabled={busy} />Automatically announce granted entries</label>
            <label className="consent-row"><input type="checkbox" checked={settings.send_photo} onChange={set('send_photo')} disabled={busy} />Attach evidence photos to security alerts</label>
            <div className="modal-actions"><button className="btn primary" type="submit" disabled={busy || !status.isLive}>Save settings</button></div>
            <div className="action-row">
              <button className="btn ghost" type="button" disabled={busy || !ready || dirty} onClick={() => perform(() => adminPost('/notify/verify', {}, 45000))}>Verify group</button>
              <button className="btn ghost" type="button" disabled={busy || !ready || dirty} onClick={() => perform(() => adminPost('/notify/test', {}, 45000))}>Send test message</button>
              <button className="btn ghost" type="button" disabled={busy || !ready || dirty} onClick={() => perform(() => adminPost('/notify/daily-report', {}, 45000))}>Send daily report now</button>
            </div>
          </form> : <p className="field-hint">Administrators manage the group connection and send announcements.</p>}
        </motion.section>
        <section className="panel">
          <div className="panel-head"><h2 className="panel-title">Announcement</h2></div>
          <form onSubmit={send}>
            <label className="login-label" htmlFor="announce-box">Message</label>
            <textarea id="announce-box" className="search-input" style={{ width: '100%', minHeight: 160 }}
              value={message} onChange={(event) => setMessage(event.target.value)} maxLength={1000}
              placeholder="Write an update for the lab group…" disabled={busy || !isAdmin} required />
            <p className="alert-time">{1000 - message.length} characters remaining. Delivery failures remain queued and retry automatically.</p>
            <div className="modal-actions"><button className="btn primary" type="submit" disabled={busy || !isAdmin || !status.isLive || !message.trim()}>{busy ? 'Working…' : 'Send via Telegram'}</button></div>
          </form>
        </section>
      </div>
      {isAdmin && <section className="panel table-panel" style={{ marginTop: 20 }}>
        <div className="panel-head"><h2 className="panel-title">Delivery history</h2><button className="btn sm ghost" type="button" disabled={busy || !ready} onClick={() => perform(() => adminPost('/notify/retry', {}, 60000))}>Retry queued messages</button></div>
        <table className="data-table"><thead><tr><th>Event</th><th>Message</th><th>Delivery</th><th>Attempts</th></tr></thead>
          <tbody>{toArray(history.data, 'notifications').map((row) => <tr key={row.id}><td>{row.alert_type}</td><td className="message-cell">{row.message}<small className="alert-time">{row.last_error}</small></td><td>{row.sent_status}</td><td>{row.delivery_attempts}</td></tr>)}
            {!toArray(history.data, 'notifications').length && <tr><td colSpan={4}><div className="empty-state">No notifications yet.</div></td></tr>}
          </tbody></table>
      </section>}
    </div>
  )
}
