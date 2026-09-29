import { useMemo, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { usePolling } from '../hooks/useApi'
import { useDialog } from '../hooks/useDialog'
import { toArray, adminPost, adminGet, apiPut, apiDelete, withAdminPrompt } from '../api/client'
import { IS_STATIC_DEMO } from '../config/runtime'
import { MOCK_USERS } from '../api/mock'
import StatusBadge from '../components/StatusBadge'
import EnrollModal from '../components/EnrollModal'

const initials = (name) =>
  String(name ?? '').split(' ').map((w) => w[0]).filter(Boolean).slice(0, 2).join('').toUpperCase() || '??'

// Shown when an action is attempted in the static demo build. These are all
// mutating endpoints; the demo has no database behind it, so we say so rather
// than letting the call fail with an opaque network error.
const DEMO_MSG = 'Not available in the static demo build — these actions need the backend API and its database.'

// A 401 means the admin token was never stored (or was rotated): the code
// above already prompted for it, so this is the "they cancelled" message.
const TOKEN_MSG = 'Admin token required — run any admin action, enter the token when asked, and try again.'

export default function Users() {
  const { data, loading, refresh } = usePolling('/users', MOCK_USERS, 8000, { enabled: !IS_STATIC_DEMO })
  const [query, setQuery] = useState('')
  const [showEnroll, setShowEnroll] = useState(false)
  const [busyId, setBusyId] = useState(null)
  const [qrView, setQrView] = useState(null)   // {name, dataUri}
  const qrDialogRef = useDialog(!!qrView, () => setQrView(null))
  const qrTitleId = 'qr-pass-title'
  const [qrError, setQrError] = useState('')
  const [rowError, setRowError] = useState('')

  const showQr = async (u) => {
    setQrError('')
    setRowError('')
    if (IS_STATIC_DEMO) return setRowError(DEMO_MSG)
    try {
      // The QR is a bearer credential for door entry, so the API demands
      // the admin token; withAdminPrompt collects it if we have none yet.
      const res = await withAdminPrompt(() =>
        adminGet(`/users/${encodeURIComponent(u.user_id)}/qr`))
      setQrView({ name: u.name ?? u.user_id, dataUri: res.qr_data_uri })
    } catch (err) {
      // Previously this set state that was only rendered inside the QR modal,
      // which never opened on failure - so the error was invisible. Surface it
      // in the table instead.
      setRowError(err.status === 401 ? TOKEN_MSG : (err.message || 'Could not load QR pass'))
    }
  }

  const rekey = async (u) => {
    if (!window.confirm(`Revoke all passes for ${u.name ?? u.user_id} and issue a new one?`)) return
    setBusyId(u.user_id)
    setQrError('')
    if (IS_STATIC_DEMO) { setBusyId(null); return setRowError(DEMO_MSG) }
    try {
      const res = await withAdminPrompt(() =>
        adminPost(`/users/${encodeURIComponent(u.user_id)}/tokens/revoke`))
      setQrView({ name: u.name ?? u.user_id, dataUri: res.qr_data_uri })
      refresh()
    } catch (err) {
      setQrError(err.status === 401 ? TOKEN_MSG : (err.message || 'Re-key failed'))
    } finally {
      setBusyId(null)
    }
  }

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
    setRowError('')
    if (IS_STATIC_DEMO) { setBusyId(null); return setRowError(DEMO_MSG) }
    try {
      await withAdminPrompt(() => apiPut(`/users/${encodeURIComponent(u.user_id)}?payment_status=${status}`))
      refresh()
    } catch (err) {
      // Was silently swallowed, leaving the dropdown showing a value the
      // server never accepted. Tell the user instead.
      setRowError(err.status === 401 ? TOKEN_MSG : (err.message || 'Could not update payment status'))
    }
    finally { setBusyId(null) }
  }

  const removeUser = async (u) => {
    if (!window.confirm(`Delete ${u.name ?? u.user_id}? Biometric data will be purged.`)) return
    setBusyId(u.user_id)
    setRowError('')
    if (IS_STATIC_DEMO) { setBusyId(null); return setRowError(DEMO_MSG) }
    try {
      await withAdminPrompt(() => apiDelete(`/users/${encodeURIComponent(u.user_id)}`))
      refresh()
    } catch (err) {
      setRowError(err.status === 401 ? TOKEN_MSG : (err.message || 'Could not delete member'))
    }
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
        {rowError && (
          <div className="form-error" style={{ marginBottom: 12 }} role="alert">
            {rowError}
            <button className="btn sm ghost" type="button" style={{ marginLeft: 10 }}
              onClick={() => setRowError('')}>Dismiss</button>
          </div>
        )}
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
                  <span style={{ display: 'inline-flex', gap: 4 }}>
                    <button className="btn sm ghost" onClick={() => showQr(u)} disabled={busyId === u.user_id} type="button" title="Show current QR pass">QR</button>
                    <button className="btn sm ghost" onClick={() => rekey(u)} disabled={busyId === u.user_id} type="button" title="Lost token: revoke + re-issue">⟳</button>
                    <button className="btn sm ghost" onClick={() => removeUser(u)} disabled={busyId === u.user_id} type="button" title="Delete member">✕</button>
                  </span>
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

      <AnimatePresence>
        {qrView && (
          <motion.div className="modal-backdrop" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={() => setQrView(null)}>
            <motion.div className="modal" style={{ width: 'min(420px, 100%)' }} onClick={(e) => e.stopPropagation()}
              ref={qrDialogRef} role="dialog" aria-modal="true" aria-labelledby={qrTitleId} tabIndex={-1}
              initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.97 }}>
              <h3 className="modal-title" id={qrTitleId}>QR Pass — {qrView.name}</h3>
              {qrError && <div className="form-error">{qrError}</div>}
              {qrView.dataUri && (
                <div className="qr-wrap">
                  <img src={qrView.dataUri} alt="QR pass" />
                  <span>Signed pass · expires in 24 h. Old passes were revoked if you just re-keyed.</span>
                </div>
              )}
              <div className="modal-actions">
                <button className="btn primary" onClick={() => setQrView(null)} type="button">Done</button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
