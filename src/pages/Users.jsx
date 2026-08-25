import { useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { usePolling } from '../hooks/useApi'
import { toArray } from '../api/client'
import { MOCK_USERS } from '../api/mock'
import StatusBadge from '../components/StatusBadge'

const initials = (name) =>
  String(name ?? '').split(' ').map((w) => w[0]).filter(Boolean).slice(0, 2).join('').toUpperCase() || '??'

export default function Users() {
  const { data, loading } = usePolling('/users', { users: MOCK_USERS })
  const [query, setQuery] = useState('')

  const rows = useMemo(() => {
    let list = toArray(data, 'users')
    if (query.trim()) {
      const q = query.trim().toLowerCase()
      list = list.filter((u) =>
        [u.name, u.user_id, u.phone].some((f) => String(f ?? '').toLowerCase().includes(q))
      )
    }
    return list
  }, [data, query])

  return (
    <div className="page-wrap">
      <div className="page-intro" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', gap: 16 }}>
        <div>
          <h1 className="page-title">Members</h1>
          <p className="page-sub">Enrolled Fab Lab users with payment and consent status.</p>
        </div>
        <input
          className="search-input"
          placeholder="Search name / ID / phone…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>

      <motion.div
        className="panel"
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45 }}
        style={{ position: 'relative' }}
      >
        {loading && <span className="loading-bar" />}
        <table className="data-table">
          <thead>
            <tr>
              <th>Member</th><th>ID</th><th>Phone</th><th>Expiry</th><th>Consent</th><th>Payment</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((u, i) => (
              <motion.tr
                key={u.user_id ?? i}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: Math.min(i * 0.04, 0.4) }}
              >
                <td>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 11 }}>
                    <div className="avatar" style={{ width: 30, height: 30, fontSize: 10.5 }}>{initials(u.name)}</div>
                    <span className="name-cell">{u.name ?? '—'}</span>
                  </div>
                </td>
                <td className="mono">{u.user_id}</td>
                <td className="mono">{u.phone ?? '—'}</td>
                <td className="mono">{u.payment_expiry ?? '—'}</td>
                <td><StatusBadge value={u.consent_given ? 'active' : 'noface'} /></td>
                <td><StatusBadge value={u.payment_status} /></td>
              </motion.tr>
            ))}
            {rows.length === 0 && !loading && (
              <tr><td colSpan={6}><div className="empty-state">No members found.<span className="mono">ENROLL USERS VIA CLI</span></div></td></tr>
            )}
          </tbody>
        </table>
      </motion.div>
    </div>
  )
}
