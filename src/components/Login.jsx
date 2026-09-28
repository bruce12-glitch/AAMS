import { useState } from 'react'
import { motion } from 'framer-motion'
import { useAuth } from '../auth/AuthContext'
import { SRMIST_SUFFIX, normalizeEmail, isSrmistEmail } from '../auth/srmAuth'
import { FablabMark } from './Logo'

/**
 * Classic entrepreneurial sign-in — calm, centered, single purpose.
 * Only @srmist.edu.in is accepted; anything else is rejected inline
 * with a clear message. No animation clutter: one soft rise-in.
 */
export default function Login() {
  const { login } = useAuth()
  const [email, setEmail] = useState('')
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
    setBusy(true)
    try {
      await login(clean)
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
          <p className="login-hint">
            Only <strong>{SRMIST_SUFFIX}</strong> addresses are evaluated. Other mail IDs are rejected automatically.
          </p>
          {error && (
            <div className="form-error" role="alert">
              {error}
            </div>
          )}
          <button className="btn primary login-btn" type="submit" disabled={busy}>
            {busy ? 'Verifying…' : 'Continue with SRMIST mail'}
          </button>
        </form>

        <div className="login-foot mono">
          FAB LAB · AAMS · Fablab, SRMIST Potheri
        </div>
      </motion.div>
    </div>
  )
}
