import { useState } from 'react'
import { motion } from 'framer-motion'
import { usePolling } from '../hooks/useApi'
import { adminPost, getAdminToken, setAdminToken } from '../api/client'
import { IS_STATIC_DEMO } from '../config/runtime'

const DEMO_MSG = 'Not available in the static demo build — sending needs the backend API with Telegram credentials.'
const EMPTY_STATUS = { telegram_enabled: false, bot_configured: false, chat_configured: false }
const MAX_LEN = 1000

/**
 * Communication portal — compose an announcement in the console,
 * deliver it to the lab Telegram group via POST /api/notify/send.
 * Every send is stored in the alerts table (audit trail) whether or
 * not Telegram delivery succeeds, and the outcome is reported honestly.
 */
export default function Communicate() {
  const status = usePolling('/notify/status', EMPTY_STATUS, 15000, { enabled: !IS_STATIC_DEMO })
  const [message, setMessage] = useState('')
  const [token, setToken] = useState(getAdminToken())
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  const s = status.data ?? EMPTY_STATUS
  const ready = s.telegram_enabled && s.bot_configured && s.chat_configured
  const remaining = MAX_LEN - message.length

  const send = async () => {
    setError('')
    setResult(null)
    if (IS_STATIC_DEMO) return setError(DEMO_MSG)
    if (!message.trim()) return setError('Write a message first.')
    if (message.trim().length > MAX_LEN) return setError(`Message exceeds ${MAX_LEN} characters.`)
    setBusy(true)
    try {
      setAdminToken(token)
      const res = await adminPost('/notify/send', { message: message.trim() })
      setResult(res)
      if (res.telegram_sent) setMessage('')
    } catch (err) {
      setError(err.message || 'Send failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="page-wrap">
      <div className="page-intro">
        <h1 className="page-title">Communicate</h1>
        <p className="page-sub">Send an announcement to the lab Telegram group — stored in the alert trail either way.</p>
      </div>

      <div className="grid-main">
        <motion.section
          className="panel"
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45 }}
        >
          <div className="panel-head">
            <h2 className="panel-title"><span className="tick" />New Announcement</h2>
            <span className={`badge ${ready ? 'active' : 'unpaid'}`}>
              <span className="badge-dot" />
              {ready ? 'telegram ready' : 'telegram pending'}
            </span>
          </div>

          <label className="login-label" htmlFor="announce-box">Message</label>
          <textarea
            id="announce-box"
            className="search-input"
            style={{ width: '100%', minHeight: 130, resize: 'vertical', lineHeight: 1.55 }}
            placeholder="e.g. Fab Lab closes at 6 PM today for maintenance…"
            value={message}
            maxLength={MAX_LEN + 50}
            onChange={(e) => setMessage(e.target.value)}
            disabled={busy}
          />
          <div className="alert-time mono" style={{ marginTop: 6 }}>
            {remaining >= 0 ? `${remaining} characters left` : `${-remaining} over limit`}
          </div>

          <div className="form-grid" style={{ marginTop: 12 }}>
            <label>Admin token
              <input
                value={token}
                onChange={(e) => setToken(e.target.value)}
                placeholder="X-Admin-Token"
                type="password"
              />
            </label>
          </div>

          {error && <div className="form-error" role="alert">{error}</div>}
          {result && (
            <div
              className="form-error"
              role="status"
              style={result.telegram_sent
                ? { borderColor: 'var(--green-line)', background: 'var(--green-bg)', color: 'var(--green-text)' }
                : undefined}
            >
              {result.telegram_sent
                ? `Sent to Telegram (alert #${result.alert_id}).`
                : `Stored as alert #${result.alert_id}, Telegram not delivered: ${result.reason}.`}
            </div>
          )}

          <div className="modal-actions">
            <button className="btn primary" onClick={send} disabled={busy} type="button">
              {busy ? 'Sending…' : 'Send via Telegram'}
            </button>
          </div>
        </motion.section>

        <motion.section
          className="panel"
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, delay: 0.12 }}
        >
          <div className="panel-head">
            <h2 className="panel-title"><span className="tick" />Channel Status</h2>
            <span className="panel-link">{status.isLive ? 'live' : 'demo'}</span>
          </div>
          <div className="kv-row"><span className="kv-key">Telegram enabled</span><span className="kv-val">{s.telegram_enabled ? 'yes' : 'no'}</span></div>
          <div className="kv-row"><span className="kv-key">Bot token set</span><span className="kv-val">{s.bot_configured ? 'yes' : 'no'}</span></div>
          <div className="kv-row"><span className="kv-key">Chat configured</span><span className="kv-val">{s.chat_configured ? 'yes' : 'no'}</span></div>
          {!ready && (
            <div className="camera-path-hint">
              <strong>To enable delivery:</strong> set <code>TELEGRAM_BOT_TOKEN</code> +{' '}
              <code>TELEGRAM_CHAT_ID</code> in <code>fablab-face-attendance/.env</code> and{' '}
              <code>alerts.telegram_enabled: true</code> in <code>config.yaml</code>, then restart the API.
              Until then, announcements are stored in the alert trail with the reason shown.
            </div>
          )}
        </motion.section>
      </div>
    </div>
  )
}
