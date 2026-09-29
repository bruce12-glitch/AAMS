import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { usePolling } from '../hooks/useApi'
import { toArray, adminPost, withAdminPrompt } from '../api/client'
import { IS_STATIC_DEMO } from '../config/runtime'
import { MOCK_ALERTS } from '../api/mock'

const SEV = ['all', 'high', 'medium', 'low']

// Guard invalid timestamps: new Date(bad).toLocaleString() returns the literal
// string "Invalid Date", which would render straight into the UI.
const fmtStamp = (iso) => {
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleString('en-IN')
}

export default function Alerts() {
  const { data, isLive, refresh } = usePolling(
    '/alerts',
    MOCK_ALERTS,
    6000,
    { enabled: !IS_STATIC_DEMO }
  )
  const [sev, setSev] = useState('all')
  const [acked, setAcked] = useState({})
  const [ackError, setAckError] = useState('')

  const list = toArray(data, 'alerts').filter((a) => sev === 'all' || String(a.severity ?? '').toLowerCase() === sev)

  const ack = async (id) => {
    setAckError('')
    // Update the UI first so the click always feels responsive.
    setAcked((m) => ({ ...m, [id]: true }))
    // In the static demo there is no endpoint to call; stop here rather than
    // firing a request that can only fail.
    if (IS_STATIC_DEMO) return
    try {
      // Acknowledging is an admin action (otherwise anyone could clear the
      // board); withAdminPrompt collects the token on a 401.
      await withAdminPrompt(() => adminPost(`/alerts/${id}/ack`))
      refresh()
    } catch (err) {
      // The server never saw it — put the button back and say why.
      setAcked((m) => { const next = { ...m }; delete next[id]; return next })
      setAckError(err.status === 401
        ? 'Admin token required to acknowledge alerts.'
        : (err.message || 'Could not acknowledge this alert'))
    }
  }

  return (
    <div className="page-wrap">
      <div className="page-intro" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', gap: 16 }}>
        <div>
          <h1 className="page-title">Security Alerts</h1>
          <p className="page-sub">Proxy attempts, unpaid entries, unknown persons and spoof detections.</p>
        </div>
        <div className="chip-row">
          {SEV.map((s) => (
            <button key={s} className={`filter-chip ${sev === s ? 'on' : ''}`} onClick={() => setSev(s)} type="button">
              {s}
            </button>
          ))}
        </div>
      </div>

      <div className="report-grid">
        {ackError && (
          <div className="form-error" style={{ gridColumn: '1 / -1' }} role="alert">
            {ackError}
            <button className="btn sm ghost" type="button" style={{ marginLeft: 10 }}
              onClick={() => setAckError('')}>Dismiss</button>
          </div>
        )}
        <AnimatePresence mode="popLayout">
          {list.map((a, i) => {
            const isAcked = a.acked === 1 || acked[a.id]
            return (
              <motion.div
                key={`${a.id}-${i}`}
                layout
                className={`alert-card ${(a.severity ?? 'low').toLowerCase()}`}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.96 }}
                transition={{ delay: Math.min(i * 0.05, 0.35), type: 'spring', stiffness: 300, damping: 28 }}
              >
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div className="alert-type">{String(a.alert_type ?? 'EVENT').replace(/_/g, ' ')}</div>
                  <div className="alert-msg">{a.message ?? '—'}</div>
                  <div className="alert-time mono">
                    {fmtStamp(a.created_at)} · severity {a.severity ?? 'low'}
                  </div>
                </div>
                {!isAcked && (
                  <button className="btn sm" onClick={() => ack(a.id)} type="button" style={{ alignSelf: 'center' }}>
                    Ack
                  </button>
                )}
              </motion.div>
            )
          })}
        </AnimatePresence>

        {list.length === 0 && (
          <motion.div className="panel" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <div className="empty-state">
              No {sev === 'all' ? '' : sev + '-severity '}alerts.
              <span className="mono">SYSTEM NOMINAL</span>
            </div>
            {!isLive && <p className="alert-time">Backend offline — sample feed shown.</p>}
          </motion.div>
        )}
      </div>
    </div>
  )
}
