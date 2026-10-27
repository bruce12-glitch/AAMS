import { IconCheck, IconX } from './icons'

/** A measured recognition result, never a fabricated confidence percentage. */
export default function EntryResult({ result }) {
  if (!result) return null
  const diagnostics = result.diagnostics
  const granted = result.decision === 'GRANTED'
  const simulation = result.source === 'simulation' || result.source === 'local'
  const notification = {
    sent: 'Telegram: message sent',
    queued: `Telegram: queued — ${result.notification?.reason || 'See Communicate.'}`,
    disabled: 'Telegram: automatic entry messages are off',
    not_requested: result.dry_run ? 'No attendance, evidence or Telegram message saved.' : 'Telegram: no new message needed',
  }[result.notification?.status]
  const quality = diagnostics?.quality
  return (
    <section className={`decision-banner ${granted ? 'granted' : 'denied'}`} aria-label="Recognition result" aria-live="polite">
      <div className="decision-icon-ring">{granted ? <IconCheck width={24} /> : <IconX width={24} />}</div>
      <div style={{ minWidth: 0, flex: 1, overflowWrap: 'anywhere' }}>
        <div className="decision-title">{simulation ? 'Simulated example' : result.dry_run ? (granted ? 'Check passed' : 'Check needs attention') : `Access ${result.decision}`}</div>
        <div className="decision-reason">{result.reason}</div>
        {result.user?.name && <div className="decision-reason">{result.user.name} · {result.user.user_id}</div>}
        {simulation && <p>No face analyzed; this is not recognition or attendance evidence.</p>}
        {!simulation && <>
          {result.recorded === true && <div className="alert-time">{granted ? 'Attendance recorded' : 'Denied attempt saved — not an attendance entry'}</div>}
          {result.duplicate && <div className="alert-time">Repeat scan ignored · no new attendance or Telegram message</div>}
          {notification && <div className="alert-time" data-testid="entry-notification">{notification}</div>}
          {diagnostics && <dl className="recognition-metrics">
            {diagnostics.face_count != null && <div><dt>Faces detected</dt><dd>{diagnostics.face_count}</dd></div>}
            <div><dt>Face comparison</dt><dd>{diagnostics.comparison_performed
              ? `${result.similarity.toFixed(3)} / threshold ${diagnostics.threshold.toFixed(3)}`
              : 'Not performed'}</dd></div>
            <div><dt>Identity result</dt><dd>{diagnostics.identity_result}</dd></div>
            <div><dt>Face quality</dt><dd>{quality ? quality.passed ? 'Passed' : 'Retake needed' : 'Not evaluated'}</dd></div>
            <div><dt>Liveness</dt><dd>{diagnostics.liveness?.status || result.liveness_status || 'unknown'}</dd></div>
            {quality?.face_width_px != null && <div><dt>Face width</dt><dd>{quality.face_width_px}px / minimum {quality.min_face_width_px}px</dd></div>}
            {quality?.blur_variance != null && <div><dt>Sharpness</dt><dd>{quality.blur_variance} / minimum {quality.blur_min}</dd></div>}
            {quality?.brightness != null && <div><dt>Brightness</dt><dd>{quality.brightness} / range {quality.brightness_min}–{quality.brightness_max}</dd></div>}
            {diagnostics.enrolled_users != null && <div><dt>Enrolled identities searched</dt><dd>{diagnostics.enrolled_users}</dd></div>}
          </dl>}
          {diagnostics?.liveness?.reason && <p className="field-hint">{diagnostics.liveness.reason}</p>}
          {diagnostics?.comparison_performed && <p className="field-hint">Cosine similarity is a match score, not an accuracy percentage.</p>}
        </>}
      </div>
    </section>
  )
}
