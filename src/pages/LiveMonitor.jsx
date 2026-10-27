import { useState } from 'react'
import { usePolling } from '../hooks/useApi'
import { simulateEntry } from '../api/client'
import { IS_STATIC_DEMO } from '../config/runtime'
import { MOCK_LIVE } from '../api/mock'
import DataNotice from '../components/DataNotice'
import WebcamAttendance from '../components/WebcamAttendance'
import SnapshotEntry from '../components/SnapshotEntry'
import EntryResult from '../components/EntryResult'

const SCENARIOS = ['authorized', 'proxy', 'unpaid', 'unknown', 'spoof', 'tailgate']

export default function LiveMonitor() {
  const live = usePolling('/dashboard/live', MOCK_LIVE, 5000, { enabled: !IS_STATIC_DEMO })
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)
  const camera = live.data?.camera || {}
  const camOnline = String(camera.status || '').toLowerCase() === 'online' || camera.fps > 0
  const runScenario = async (scenario) => {
    setBusy(true)
    try { setResult({ ...await simulateEntry(scenario), source: 'simulation' }) }
    finally { setBusy(false) }
  }
  return (
    <div className="page-wrap">
      <DataNotice error={live.error} loading={live.loading} />
      <div className="page-intro">
        <h1 className="page-title">Live Monitor</h1>
        <p className="page-sub">Automatic webcam attendance and a separate, no-write recognition check.</p>
      </div>
      <div className="grid-main">
        <div className="stack">
          <WebcamAttendance onResult={setResult} />
          <EntryResult result={result} />
          <details className="panel">
            <summary className="panel-title" style={{ cursor: 'pointer' }}>Optional lab camera and pipeline overview</summary>
            <p>{camOnline ? `Lab camera online · ${camera.fps} FPS` : 'Optional lab camera is on standby. It is separate from the laptop webcam above.'}</p>
            <p className="field-hint">A lab camera is not required for this laptop demo. For dedicated door hardware set camera.source and capture.enabled in config.yaml.</p>
            <p className="field-hint">Pipeline overview, not live telemetry: detect → quality → ArcFace embedding → identity → payment/liveness policy → attendance.</p>
          </details>
        </div>
        <div className="stack">
          <SnapshotEntry />
          <details className="panel">
            <summary className="panel-title" style={{ cursor: 'pointer' }}>Scenario simulator — no real CV</summary>
            <p className="field-hint">These buttons show example decisions only. They do not test your photo, recognition accuracy or Telegram.</p>
            <div className="chip-row">
              {SCENARIOS.map((scenario) => <button key={scenario} className="scenario-chip" type="button" disabled={busy}
                onClick={() => runScenario(scenario)}>{scenario}</button>)}
            </div>
          </details>
        </div>
      </div>
    </div>
  )
}
