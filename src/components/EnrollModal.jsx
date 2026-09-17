import { useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { adminPost, fileToDataUri, setAdminToken, getAdminToken } from '../api/client'
import { IS_STATIC_DEMO } from '../config/runtime'

const EMPTY = {
  user_id: '', name: '', phone: '',
  payment_status: 'active', payment_expiry: '', consent: false
}

export default function EnrollModal({ open, onClose, onEnrolled }) {
  const [form, setForm] = useState(EMPTY)
  const [previews, setPreviews] = useState([])
  const [token, setToken] = useState(getAdminToken())
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const fileRef = useRef(null)

  const set = (k) => (e) =>
    setForm((f) => ({ ...f, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }))

  const pickFiles = async (list) => {
    setError('')
    const arr = Array.from(list ?? []).slice(0, 8)
    const uris = []
    const problems = []
    for (const f of arr) {
      try {
        uris.push(await fileToDataUri(f))
      } catch (err) {
        // Collect, don't overwrite: previously the last failure won and
        // earlier ones were lost, so the user saw only one bad file.
        problems.push(err.message)
      }
    }
    setPreviews(uris)
    if (problems.length) {
      setError(
        `${problems.length} of ${arr.length} photo(s) rejected: ${problems.join('; ')}`
      )
    }
  }

  const submit = async () => {
    setError('')
    if (!form.user_id.trim() || !form.name.trim()) return setError('User ID and Name are required')
    if (!previews.length) return setError('Add at least one face photo')
    if (!form.consent) return setError('Consent is required for biometric enrollment')
    // Enrollment writes to the database and computes ArcFace embeddings
    // server-side. The static demo has neither, so be explicit.
    if (IS_STATIC_DEMO) {
      return setError(
        'Enrollment needs the backend API and its database — not available in the static demo build.'
      )
    }

    setBusy(true)
    try {
      setAdminToken(token)
      const res = await adminPost('/users/enroll', {
        ...form,
        consent_given: form.consent,
        images: previews
      })
      setResult(res)
      onEnrolled?.(res)
    } catch (err) {
      setError(err.message || 'Enrollment failed')
    } finally {
      setBusy(false)
    }
  }

  const close = () => {
    setForm(EMPTY); setPreviews([]); setResult(null); setError('')
    onClose()
  }

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="modal-backdrop"
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          onClick={close}
        >
          <motion.div
            className="modal"
            onClick={(e) => e.stopPropagation()}
            initial={{ opacity: 0, y: 24, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 16, scale: 0.98 }}
            transition={{ type: 'spring', stiffness: 340, damping: 30 }}
          >
            {!result ? (
              <>
                <h3 className="modal-title">Enroll Member</h3>
                <p className="modal-sub">
                  Photos are processed server-side — quality-gated ArcFace embeddings (§17).
                </p>

                <div className="form-grid">
                  <label>User ID *<input value={form.user_id} onChange={set('user_id')} placeholder="e.g. SAMPLE-0001" /></label>
                  <label>Full name *<input value={form.name} onChange={set('name')} placeholder="Member full name" /></label>
                  <label>Phone<input value={form.phone} onChange={set('phone')} placeholder="Optional contact number" /></label>
                  <label>Payment status
                    <select value={form.payment_status} onChange={set('payment_status')}>
                      <option value="active">active</option>
                      <option value="pending">pending</option>
                      <option value="expired">expired</option>
                      <option value="inactive">inactive</option>
                    </select>
                  </label>
                  <label>Payment expiry<input type="date" value={form.payment_expiry} onChange={set('payment_expiry')} /></label>
                  <label>Admin token<input value={token} onChange={(e) => setToken(e.target.value)} placeholder="X-Admin-Token" type="password" /></label>
                </div>

                <p className="field-hint">
                  Admin token is required — it protects the enrollment endpoint.
                  Set it as <code>API_ADMIN_PASSWORD</code> in{' '}
                  <code>fablab-face-attendance/.env</code>. If it is left unset the
                  API runs in dev-open mode and the field can stay empty.
                </p>

                <div className={`dropzone ${previews.length ? 'has-files' : ''}`} onClick={() => fileRef.current?.click()}>
                  <input ref={fileRef} type="file" accept="image/*" multiple hidden onChange={(e) => pickFiles(e.target.files)} />
                  {previews.length === 0
                    ? <>📸 Click to add face photos<span>3–5 shots · front + slight angles · JPG/PNG ≤ 8 MB each</span></>
                    : <div className="preview-row">
                      {previews.map((p, i) => <img key={i} src={p} alt={`shot ${i + 1}`} />)}
                      <span>{previews.length} selected</span>
                    </div>}
                </div>

                <label className="consent-row">
                  <input type="checkbox" checked={form.consent} onChange={set('consent')} />
                  Student consents to facial biometric storage for Fab Lab access (§26.2)
                </label>

                {error && <div className="form-error">{error}</div>}

                <div className="modal-actions">
                  <button className="btn ghost" onClick={close} disabled={busy} type="button">Cancel</button>
                  <button className="btn primary" onClick={submit} disabled={busy} type="button">
                    {busy ? 'Processing…' : 'Enroll'}
                  </button>
                </div>
              </>
            ) : (
              <>
                <h3 className="modal-title">✅ Enrolled {form.name}</h3>
                <div className="kv-row"><span className="kv-key">Embeddings stored</span><span className="kv-val">{result.embeddings_stored}</span></div>
                <div className="kv-row"><span className="kv-key">Photos rejected by quality gate</span><span className="kv-val">{result.images_rejected}</span></div>
                <div className="qr-wrap">
                  {result.qr_data_uri && <img src={result.qr_data_uri} alt="QR pass" />}
                  <span>Signed QR pass — valid 24 h, regenerate anytime</span>
                </div>
                <div className="modal-actions">
                  <button className="btn primary" onClick={close} type="button">Done</button>
                </div>
              </>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
