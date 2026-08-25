import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { usePolling } from '../hooks/useApi'
import { toArray, apiPost } from '../api/client'
import { MOCK_ALERTS } from '../api/mock'

const SEV = ['all', 'high', 'medium', 'low']

export default function Alerts() {
  const { data, isLive, refresh } = usePolling('/alerts', { alerts: MOCK_ALERTS }, 6000)
  const [sev, setSev] = useState('all')
  const [acked, setAcked] = useState({})

  const list = toArray(data, 'alerts').filter((a) => sev === 'all' || String(a.severity ?? '').toLowerCase() === sev)

  const ack = async (id) => {
    setAcked((m) => ({ ...m, [id]: true }))
    try {
      await apiPost(`/alerts/${id}/ack`)
      refresh()
    } catch {
      /* optimistic — stays acked in UI; server state refreshes on next poll */
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
                    {new Date(a.created_at).toLocaleString('en-IN') || ''} · severity {a.severity ?? 'low'}
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
