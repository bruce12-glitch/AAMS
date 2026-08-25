import { useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { usePolling } from '../hooks/useApi'
import { toArray, adminPost, apiPut, apiDelete } from '../api/client'
import { MOCK_USERS } from '../api/mock'
import StatusBadge from '../components/StatusBadge'
import EnrollModal from '../components/EnrollModal'

const initials = (name) =>
  String(name ?? '').split(' ').map((w) => w[0]).filter(Boolean).slice(0, 2).join('').toUpperCase() || '??'

export default function Users() {
  const { data, loading, refresh } = usePolling('/users', { users: MOCK_USERS })
  const [query, setQuery] = useState('')
  const [showEnroll, setShowEnroll] = useState(false)
  const [busyId, setBusyId] = useState(null)

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

  const setPayment = async (u, status) => {
    setBusyId(u.user_id)
    try {
      await apiPut(`/users/${encodeURIComponent(u.user_id)}?payment_status=${status}`)
      refresh()
    } catch { /* poll will reconcile; surface via badge */ }
    finally { setBusyId(null) }
  }

  const removeUser = async (u) => {
    if (!window.confirm(`Delete ${u.name ?? u.user_id}? Biometric data will be purged.`)) return
    setBusyId(u.user_id)
    try {
      await apiDelete(`/users/${encodeURIComponent(u.user_id)}`)
      refresh()
    } catch { /* ignore */ }
    finally { setBusyId(null) }
  }

  return (
    <div className="page-wrap">
      <div className="page-intro" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', gap: 16 }}>
        <div>
          <h1 className="page-title">Members</h1>
          <p className="page-sub">Enrolled Fab Lab users with payment and consent status.</p>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <input
            className="search-input"
            placeholder="Search name / ID / phone…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button className="btn primary" onClick={() => setShowEnroll(true)} type="button">＋ Enroll</button>
        </div>
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
              <th>Member</th><th>ID</th><th>Phone</th><th>Biometrics</th><th>Payment</th><th></th>
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
                <td><StatusBadge value={u.enrolled ? 'active' : 'noface'} /></td>
                <td>
                  <span style={{ display: 'inline-flex', gap: 6, alignItems: 'center' }}>
                    <StatusBadge value={u.payment_status} />
                    <select
                      className="mini-select"
                      value={String(u.payment_status ?? 'inactive')}
                      disabled={busyId === u.user_id}
                      onChange={(e) => setPayment(u, e.target.value)}
                    >
                      <option value="active">active</option>
                      <option value="pending">pending</option>
                      <option value="expired">expired</option>
                      <option value="inactive">inactive</option>
                    </select>
                  </span>
                </td>
                <td>
                  <button className="btn sm ghost" onClick={() => removeUser(u)} disabled={busyId === u.user_id} type="button">✕</button>
                </td>
              </motion.tr>
            ))}
            {rows.length === 0 && !loading && (
              <tr><td colSpan={6}><div className="empty-state">No members found.<span className="mono">USE ＋ ENROLL TO ADD</span></div></td></tr>
            )}
          </tbody>
        </table>
      </motion.div>

      <EnrollModal open={showEnroll} onClose={() => setShowEnroll(false)} onEnrolled={() => refresh()} />
    </div>
  )
}
