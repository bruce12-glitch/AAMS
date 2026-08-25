import { useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { usePolling } from '../hooks/useApi'
import { apiPost, fileToDataUri } from '../api/client'
import { MOCK_LIVE } from '../api/mock'
import { IconCheck, IconX } from '../components/icons'

const PIPELINE = [
  'TOKEN_DETECTED',
  'FACE_DETECTED',
  'QUALITY_CHECKED',
  'LIVENESS_CHECKED',
  'MATCHED',
  'DECISION_MADE'
]

const SCENARIOS = ['authorized', 'proxy', 'unpaid', 'unknown', 'spoof', 'tailgate']

const REDUCED_SCAN =
  typeof window !== 'undefined' &&
  window.matchMedia('(prefers-reduced-motion: reduce)').matches

export default function LiveMonitor() {
  const live = usePolling('/dashboard/live', MOCK_LIVE, 5000)
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)

  // snapshot test state
  const [mode, setMode] = useState('token_face')
  const [photoUri, setPhotoUri] = useState('')
  const [burstUris, setBurstUris] = useState([])
  const [tokenValue, setTokenValue] = useState('')
  const [skipLiveness, setSkipLiveness] = useState(true)
  const [cvError, setCvError] = useState('')

  const mainRef = useRef(null)
  const burstRef = useRef(null)

  const camera = live.data?.camera ?? MOCK_LIVE.camera
  const camOnline = String(camera?.status ?? '').toLowerCase() === 'online' || camera?.fps > 0
  const steps = Array.isArray(live.data?.steps) ? live.data.steps : ['IDLE']

  const runScenario = async (scenario) => {
    setBusy(true)
    setResult(null)
    try {
      const res = await apiPost('/entry/simulate', { scenario }, 4000)
      setResult({ ...res, source: 'api' })
    } catch {
      setResult(null)
    } finally {
      setBusy(false)
    }
  }

  const runSnapshot = async () => {
    setCvError('')
    setResult(null)
    if (!photoUri) return setCvError('Pick a face photo first')
    if (mode === 'token_face' && !tokenValue.trim())
      return setCvError('Enter a token value (user ID or full signed QR JSON)')

    setBusy(true)
    try {
      const body = {
        image_b64: photoUri,
        liveness_frames_b64: skipLiveness ? [] : burstUris,
        skip_liveness: skipLiveness || burstUris.length < 2
      }
      const path = mode === 'token_face' ? '/entry/process' : '/entry/face-only'
      if (mode === 'token_face') body.token_value = tokenValue.trim()
      const res = await apiPost(path, body, 60000)
      setResult({ ...res, source: 'api' })
    } catch (err) {
      setCvError(err.message || 'Entry request failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="page-wrap">
      <div className="page-intro">
        <h1 className="page-title">Live Monitor</h1>
        <p className="page-sub">Entrance pipeline status and real CV entry testing.</p>
      </div>

      <div className="grid-main">
        <div className="stack">
          <motion.section
            className="panel"
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45 }}
          >
            <div className="panel-head">
              <h2 className="panel-title"><span className="tick" />Entrance Camera</h2>
              <span className={`badge ${camOnline ? 'active' : 'neutral'}`}>
                <span className="badge-dot" />
                {camOnline ? 'online' : 'standby'}
              </span>
            </div>

            <div
              style={{
                aspectRatio: '16 / 8.2',
                borderRadius: 12,
                border: '1px solid var(--border)',
                background:
                  'repeating-linear-gradient(0deg, rgba(34,211,238,.03) 0 1px, transparent 1px 4px), radial-gradient(420px 200px at 50% 40%, rgba(34,211,238,.06), transparent 70%), rgba(255,255,255,.02)',
                display: 'grid',
                placeItems: 'center',
                position: 'relative',
                overflow: 'hidden'
              }}
            >
              <motion.div
                animate={REDUCED_SCAN ? {} : { y: ['-100%', '400%'] }}
                transition={{ duration: 3.2, repeat: Infinity, ease: 'linear' }}
                style={{
                  position: 'absolute', left: 0, right: 0, height: 56,
                  background: 'linear-gradient(180deg, transparent, rgba(34,211,238,.07), transparent)',
                  pointerEvents: 'none'
                }}
              />
              <div style={{ textAlign: 'center' }}>
                <div className="mono" style={{ color: 'var(--text-low)', fontSize: 11, letterSpacing: 3 }}>
                  {camOnline ? `CAM 0 · ${camera.fps} FPS · 1280×720` : 'CAMERA STANDBY'}
                </div>
                <div style={{ marginTop: 8, fontSize: 13, color: 'var(--text-mid)' }}>
                  {camOnline ? 'Monitoring entrance…' : 'Test entry with a snapshot below'}
                </div>
              </div>
            </div>

            <div className="pipeline" style={{ marginTop: 16 }}>
              {PIPELINE.map((step) => {
                const hot =
                  result?.decision && steps.includes(step) ||
                  ['MATCHED', 'DECISION_MADE'].includes(step) && result?.decision
                return (
                  <div key={step} className={`pipeline-step ${result?.decision ? 'hot' : ''}`}>
                    <span className="step-node" />
                    {step.replace(/_/g, ' ')}
                  </div>
                )
              })}
            </div>
          </motion.section>

          <AnimatePresence mode="wait">
            {result && (
              <motion.section
                key={`${result.tag}-${result.decision}-${Math.random()}`}
                className={`decision-banner ${result.decision === 'GRANTED' ? 'granted' : 'denied'}`}
                initial={{ opacity: 0, scale: 0.94, y: 12 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.96, y: -8 }}
                transition={{ type: 'spring', stiffness: 320, damping: 26 }}
              >
                <span className="decision-scanline" />
                <div className="decision-icon-ring">
                  {result.decision === 'GRANTED'
                    ? <IconCheck width={24} height={24} />
                    : <IconX width={24} height={24} />}
                </div>
                <div>
                  <div className="decision-title" style={{ color: result.decision === 'GRANTED' ? 'var(--green)' : 'var(--red)' }}>
                    Access {result.decision}
                  </div>
                  <div className="decision-reason">{result.reason}</div>
                  {typeof result.similarity === 'number' && (
                    <div className="alert-time mono">
                      similarity {result.similarity.toFixed(2)} · liveness {result.liveness_status ?? 'n/a'}
                      {result.face_count > 0 ? ` · faces ${result.face_count}` : ''}
                      {result.occupant_state ? ` · ${result.occupant_state}` : ''}
                    </div>
                  )}
                </div>
                <span
                  className="badge neutral"
                  style={{ marginLeft: 'auto' }}
                  title={result.source === 'local' ? 'Backend unreachable — simulated locally' : 'Response from API'}
                >
                  {result.source === 'local' ? 'local sim' : 'api'}
                </span>
              </motion.section>
            )}
          </AnimatePresence>

          {cvError && (
            <motion.div className="form-error" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              {cvError}
            </motion.div>
          )}
        </div>

        <div className="stack">
          <motion.section
            className="panel"
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.15 }}
          >
            <div className="panel-head">
              <h2 className="panel-title"><span className="tick" />Snapshot Entry Test</h2>
            </div>
            <p style={{ fontSize: 12.5, color: 'var(--text-mid)', lineHeight: 1.55, margin: '0 0 14px' }}>
              Runs the real pipeline server-side: detect → quality → ArcFace embed → match → policy.
            </p>

            <div className="chip-row" style={{ marginBottom: 12 }}>
              <button className={`filter-chip ${mode === 'token_face' ? 'on' : ''}`} onClick={() => setMode('token_face')} type="button">Token + Face</button>
              <button className={`filter-chip ${mode === 'face_only' ? 'on' : ''}`} onClick={() => setMode('face_only')} type="button">Face only</button>
            </div>

            <button className={`dropzone slim ${photoUri ? 'has-files' : ''}`} onClick={() => mainRef.current?.click()} type="button">
              <input ref={mainRef} type="file" accept="image/*" hidden
                onChange={async (e) => { try { setPhotoUri(await fileToDataUri(e.target.files?.[0])) } catch (err) { setCvError(err.message) } }} />
              {photoUri
                ? <img src={photoUri} alt="snapshot" style={{ maxHeight: 110, borderRadius: 8 }} />
                : <>📷 Pick entrance snapshot<span>JPG / PNG — face clearly visible</span></>}
            </button>

            {mode === 'token_face' && (
              <input className="search-input" style={{ width: '100%', marginTop: 10 }}
                placeholder="Token (user ID or signed QR JSON)"
                value={tokenValue} onChange={(e) => setTokenValue(e.target.value)} />
            )}

            <label className="consent-row" style={{ marginTop: 10 }}>
              <input type="checkbox" checked={skipLiveness}
                onChange={(e) => setSkipLiveness(e.target.checked)} />
              Skip blink liveness (single snapshot)
            </label>

            {!skipLiveness && (
              <>
                <button className={`dropzone slim ${burstUris.length ? 'has-files' : ''}`}
                  onClick={() => burstRef.current?.click()} type="button" style={{ marginTop: 10 }}>
                  <input ref={burstRef} type="file" accept="image/*" multiple hidden
                    onChange={async (e) => {
                      const uris = []
                      for (const f of Array.from(e.target.files ?? []).slice(0, 12)) {
                        try { uris.push(await fileToDataUri(f)) } catch (err) { setCvError(err.message) }
                      }
                      setBurstUris(uris)
                    }} />
                  {burstUris.length
                    ? <span>{burstUris.length} burst frames ready</span>
                    : <>🎞️ Pick 4–10 frame burst<span>short sequence capturing a blink</span></>}
                </button>
                {burstUris.length > 0 && burstUris.length < 4 && (
                  <p className="alert-time" style={{ marginTop: 6 }}>Fewer than 4 frames — liveness will stay “unknown”.</p>
                )}
              </>
            )}

            <button className="btn primary" style={{ width: '100%', marginTop: 14 }}
              onClick={runSnapshot} disabled={busy} type="button">
              {busy ? 'Running CV pipeline…' : 'Process Entry'}
            </button>
          </motion.section>

          <motion.section
            className="panel"
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.25 }}
          >
            <div className="panel-head">
              <h2 className="panel-title"><span className="tick" />Scenario Simulator</h2>
            </div>
            <div className="chip-row">
              {SCENARIOS.map((sc) => (
                <button key={sc} className="scenario-chip" onClick={() => runScenario(sc)} disabled={busy} type="button">
                  {sc}
                </button>
              ))}
            </div>
          </motion.section>
        </div>
      </div>
    </div>
  )
}
