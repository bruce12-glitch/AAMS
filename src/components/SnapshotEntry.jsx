import { useRef, useState } from 'react'
import { apiPost, fileToDataUri } from '../api/client'
import { usePolling } from '../hooks/useApi'
import { IS_STATIC_DEMO } from '../config/runtime'
import CameraCapture from './CameraCapture'
import EntryResult from './EntryResult'

export default function SnapshotEntry() {
  const members = usePolling('/users', { users: [] }, 5000, { enabled: !IS_STATIC_DEMO })
  const [mode, setMode] = useState('face_only')
  const [photo, setPhoto] = useState('')
  const [burst, setBurst] = useState([])
  const [token, setToken] = useState('')
  const [skipLiveness, setSkipLiveness] = useState(true)
  const [cameraOpen, setCameraOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const inputRef = useRef(null)
  const selected = members.data?.users?.find((user) => user.user_id === token)
  const resetResult = () => { setResult(null); setError('') }
  const setCapture = (shots) => {
    resetResult()
    setPhoto(shots.at(-1) || '')
    setBurst(shots.length > 1 ? shots : [])
  }
  const run = async (dryRun) => {
    resetResult()
    if (!photo) return setError('Upload a clear original photo or capture one from your webcam first.')
    if (mode === 'token_face' && !token.trim()) return setError('Select the registered member or paste their current signed QR pass.')
    if (!skipLiveness && burst.length < 4) return setError('Capture a blink sequence with the webcam, or explicitly enable the still-photo demo option.')
    setBusy(true)
    try {
      const response = await apiPost(mode === 'face_only' ? '/entry/face-only' : '/entry/process', {
        image_b64: photo, token_value: mode === 'token_face' ? token.trim() : undefined,
        liveness_frames_b64: skipLiveness ? [] : burst,
        skip_liveness: skipLiveness, dry_run: dryRun,
        continuous: !dryRun,
      }, 120000)
      setResult(response)
    } catch (err) {
      setError(err.name === 'AbortError' ? 'Recognition timed out. Check the backend and initialize the model on Dashboard.' : err.message || 'Recognition request failed.')
    } finally { setBusy(false) }
  }
  const box = result?.diagnostics?.bbox
  const size = result?.diagnostics?.image_size
  return (
    <section className="panel" aria-label="Photo recognition test">
      <div className="panel-head"><h2 className="panel-title">Photo & camera check</h2></div>
      <p className="field-hint">First check recognition without saving anything. Record entry only when you are ready.</p>
      <div className="chip-row" style={{ marginBottom: 12 }}>
        <button className={`filter-chip ${mode === 'face_only' ? 'on' : ''}`} disabled={busy} type="button"
          onClick={() => { setMode('face_only'); resetResult() }}>Face only</button>
        <button className={`filter-chip ${mode === 'token_face' ? 'on' : ''}`} disabled={busy} type="button"
          onClick={() => { setMode('token_face'); resetResult() }}>Member + Face</button>
      </div>
      {mode === 'token_face' && <div className="form-grid" style={{ gridTemplateColumns: '1fr', marginBottom: 12 }}>
        <label>Registered member
          <select aria-label="Registered member" value={selected ? token : ''} disabled={busy || members.loading}
            onChange={(event) => { setToken(event.target.value); resetResult() }}>
            <option value="">Select a member…</option>
            {(members.data?.users || []).filter((user) => user.active).map((user) => <option value={user.user_id} key={user.user_id}>
              {user.name} · {user.user_id} · {user.enrolled ? 'face enrolled' : 'NOT enrolled'}
            </option>)}
          </select>
        </label>
        <label>Student ID or signed QR pass
          <input value={token} disabled={busy} placeholder="Student ID or full signed QR JSON"
            onChange={(event) => { setToken(event.target.value); resetResult() }} />
        </label>
        {selected && !selected.enrolled && <p className="form-error">This profile has no enrolled face. Open Members → Enroll face before matching.</p>}
        {members.error && <p role="alert">Cannot load members: {members.error}</p>}
      </div>}
      {photo && <div className="snapshot-preview">
        <div style={{ position: 'relative', display: 'inline-block' }}>
          <img src={photo} alt="Photo being checked" />
          {box && size && <span aria-label="Detected face bounding box" style={{ position: 'absolute', pointerEvents: 'none',
            border: '2px solid var(--cyan)', left: `${100 * box[0] / size.width}%`, top: `${100 * box[1] / size.height}%`,
            width: `${100 * (box[2] - box[0]) / size.width}%`, height: `${100 * (box[3] - box[1]) / size.height}%` }} />}
        </div>
      </div>}
      <div className="snapshot-actions">
        <input ref={inputRef} type="file" accept="image/*" hidden aria-label="Upload test photo" disabled={busy}
          onChange={async (event) => {
            const file = event.target.files?.[0]
            if (!file) return
            setBusy(true)
            resetResult()
            try { setCapture([await fileToDataUri(file)]) } catch (err) { setError(err.message) }
            finally { setBusy(false); event.target.value = '' }
          }} />
        <button className="btn ghost" type="button" disabled={busy} onClick={() => inputRef.current?.click()}>Upload photo</button>
        <button className="btn ghost" type="button" disabled={busy} onClick={() => setCameraOpen(true)}>
          {skipLiveness ? 'Capture from webcam' : 'Capture blink sequence'}</button>
      </div>
      <label className="consent-row" style={{ marginTop: 12 }}>
        <input type="checkbox" checked={skipLiveness} disabled={busy}
          onChange={(event) => { setSkipLiveness(event.target.checked); setBurst([]); resetResult() }} />
        Still-photo demo: skip liveness (not anti-spoof verified)
      </label>
      <p className="field-hint">{skipLiveness
        ? 'A still photo can test identity matching, but cannot prove a live person. Use original photos, not AI-enhanced portraits.'
        : `Capture a short webcam sequence and blink naturally. ${burst.length ? `${burst.length} frames captured.` : 'A single uploaded photo is not enough.'}`}</p>
      {IS_STATIC_DEMO && <p role="alert">Connect a live backend. This static site cannot analyze photos.</p>}
      {error && <div className="form-error" role="alert">{error}</div>}
      <div className="snapshot-actions">
        <button className="btn primary" type="button" disabled={busy || IS_STATIC_DEMO} onClick={() => run(true)}>{busy ? 'Checking…' : 'Check photo — no attendance'}</button>
        <button className="btn ghost" type="button" disabled={busy || IS_STATIC_DEMO} onClick={() => run(false)}>Record entry</button>
      </div>
      {result && <div style={{ marginTop: 16 }}><EntryResult result={result} /></div>}
      <CameraCapture open={cameraOpen} maxShots={skipLiveness ? 1 : 10} burst={!skipLiveness}
        onDone={setCapture} onClose={() => setCameraOpen(false)} />
    </section>
  )
}
