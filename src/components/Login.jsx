import { useState } from 'react'
import { motion } from 'framer-motion'
import { useAuth } from '../auth/AuthContext'
import { SRMIST_SUFFIX, normalizeEmail, isSrmistEmail } from '../auth/srmAuth'
import { FablabMark } from './Logo'

/**
 * Classic entrepreneurial sign-in — calm, centered, single purpose.
 * SRMIST email + the shared AAMS showcase password. Only
 * @srmist.edu.in is accepted; anything else is rejected inline.
 * One soft rise-in — no animation clutter.
 */
export default function Login() {
  const { login } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const submit = async (e) => {
    e?.preventDefault()
    setError('')
    const clean = normalizeEmail(email)
    if (!clean) return setError('Enter your SRMIST email to continue.')
    if (!isSrmistEmail(clean)) {
      return setError(`Only ${SRMIST_SUFFIX} mail IDs are allowed — other domains cannot access this console.`)
    }
    if (!password) return setError('Enter the AAMS access password.')
    setBusy(true)
    try {
      await login(clean, password)
    } catch (err) {
      setError(err.message || 'Sign-in failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="login-wrap">
      <motion.div
        className="login-card"
        initial={{ opacity: 0, y: 22 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      >
        <div className="login-brand">
          <FablabMark size={132} />
          <div className="login-inst">SRM Institute of Science and Technology</div>
          <h1 className="login-title">FacePass Fab Lab</h1>
          <p className="login-sub">Smart access &amp; attendance for the Fab Lab — members only.</p>
        </div>

        <form onSubmit={submit} className="login-form">
          <label className="login-label" htmlFor="srm-email">
            SRMIST email
          </label>
          <input
            id="srm-email"
            className="search-input login-input"
            type="email"
            autoComplete="email"
            placeholder={`you${SRMIST_SUFFIX}`}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={busy}
          />
          <label className="login-label" htmlFor="srm-password" style={{ marginTop: 12 }}>
            Password
          </label>
          <input
            id="srm-password"
            className="search-input login-input"
            type="password"
            autoComplete="current-password"
            placeholder="Enter the AAMS access password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={busy}
          />
          <p className="login-hint">
            Use your @srmist.edu.in address and AAMS access password. Administrators use their separate administrator password.
          </p>
          {error && (
            <div className="form-error" role="alert">
              {error}
            </div>
          )}
          <button className="btn primary login-btn" type="submit" disabled={busy}>
            {busy ? 'Verifying…' : 'Sign in'}
          </button>
        </form>

        <div className="login-foot mono">
          FAB LAB · AAMS · Fablab, SRMIST Potheri
        </div>
      </motion.div>
    </div>
  )
}
