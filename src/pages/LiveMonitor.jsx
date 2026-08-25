import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { usePolling } from '../hooks/useApi'
import { simulateEntry, SIM_SCENARIOS } from '../api/client'
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

const SCENARIOS = Object.keys(SIM_SCENARIOS)

export default function LiveMonitor() {
  const live = usePolling('/dashboard/live', MOCK_LIVE, 5000)
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)

  const camera = live.data?.camera ?? MOCK_LIVE.camera
  const camOnline = String(camera?.status ?? '').toLowerCase() === 'online' || camera?.fps > 0
  const steps = Array.isArray(live.data?.steps) ? live.data.steps : ['IDLE']

  const run = async (scenario) => {
    setBusy(true)
    setResult(null)
    try {
      const res = await simulateEntry(scenario)
      setResult(res)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="page-wrap">
      <div className="page-intro">
        <h1 className="page-title">Live Monitor</h1>
        <p className="page-sub">Entrance pipeline status and scenario simulator for testing the decision matrix.</p>
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
                  {camOnline ? 'Monitoring entrance…' : 'Waiting for backend camera service'}
                </div>
              </div>
            </div>

            <div className="pipeline" style={{ marginTop: 16 }}>
              {PIPELINE.map((step) => (
                <div key={step} className={`pipeline-step ${steps.includes(step) ? 'hot' : ''}`}>
                  <span className="step-node" />
                  {step.replace(/_/g, ' ')}
                </div>
              ))}
            </div>
          </motion.section>

          <AnimatePresence mode="wait">
            {result && (
              <motion.section
                key={`${result.tag}-${result.decision}-${Date.now()}`}
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
        </div>

        <motion.section
          className="panel"
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, delay: 0.15 }}
        >
          <div className="panel-head">
            <h2 className="panel-title"><span className="tick" />Entry Simulator</h2>
          </div>
          <p style={{ fontSize: 12.5, color: 'var(--text-mid)', lineHeight: 1.55, margin: '0 0 14px' }}>
            Fire a scenario through the access policy engine (§11.2 decision matrix). Each run is logged to the entry trail.
          </p>
          <div className="chip-row">
            {SCENARIOS.map((sc) => (
              <button key={sc} className="scenario-chip" onClick={() => run(sc)} disabled={busy} type="button">
                {sc}
              </button>
            ))}
          </div>

          <div className="kv-row" style={{ marginTop: 18 }}>
            <span className="kv-key">Match threshold</span>
            <span className="kv-val">0.45</span>
          </div>
          <div className="kv-row">
            <span className="kv-key">Mode</span>
            <span className="kv-val">TOKEN + FACE</span>
          </div>
          <div className="kv-row">
            <span className="kv-key">Liveness</span>
            <span className="kv-val">BLINK (EAR)</span>
          </div>
        </motion.section>
      </div>
    </div>
  )
}

const REDUCED_SCAN =
  typeof window !== 'undefined' &&
  window.matchMedia('(prefers-reduced-motion: reduce)').matches
