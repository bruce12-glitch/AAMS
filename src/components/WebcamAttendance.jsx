import { useEffect, useRef, useState } from 'react'
import { apiPost } from '../api/client'
import { IS_STATIC_DEMO } from '../config/runtime'

/** Laptop camera stays in the browser; only a bounded burst goes to the API. */
export default function WebcamAttendance({ onResult }) {
  const videoRef = useRef(null)
  const resultRef = useRef(onResult)
  const [running, setRunning] = useState(false)
  const [bypass, setBypass] = useState(false)
  const [status, setStatus] = useState('Camera off')
  const [error, setError] = useState('')
  useEffect(() => { resultRef.current = onResult }, [onResult])

  useEffect(() => {
    if (!running) return undefined
    let cancelled = false
    let stream
    let timer
    const controller = new AbortController()
    const schedule = (fn, ms) => { timer = setTimeout(fn, ms) }
    const stopWhenHidden = () => { if (document.hidden) setRunning(false) }
    document.addEventListener('visibilitychange', stopWhenHidden)

    const scan = async () => {
      if (cancelled) return
      const video = videoRef.current
      if (!video?.videoWidth || video.readyState < 2) {
        schedule(scan, 300)
        return
      }
      const frames = []
      const capture = async () => {
        if (cancelled) return
        try {
          const canvas = document.createElement('canvas')
          const scale = Math.min(1, 960 / Math.max(video.videoWidth, video.videoHeight))
          canvas.width = Math.round(video.videoWidth * scale)
          canvas.height = Math.round(video.videoHeight * scale)
          canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height)
          frames.push(canvas.toDataURL('image/jpeg', 0.85))
          if (!bypass && frames.length < 10) {
            setStatus('Look at the camera and blink naturally…')
            schedule(capture, 200)
            return
          }
          setStatus('Checking identity and attendance…')
          const result = await apiPost('/entry/face-only', {
            image_b64: frames[frames.length - 1],
            liveness_frames_b64: bypass ? [] : frames,
            skip_liveness: bypass,
            continuous: true,
          }, 120000, controller.signal)
          if (cancelled) return
          resultRef.current?.({ ...result, source: 'api' })
          setStatus(result.duplicate
            ? result.decision === 'GRANTED' ? 'Already recorded — waiting for the next person' : `Repeated check: ${result.reason}`
            : result.decision === 'GRANTED'
              ? `Attendance recorded: ${result.user?.name || result.recognized_id}. Telegram follows your Communicate settings.`
              : result.reason || 'No match — face the camera and try again')
          // Sequential requests, bounded camera traffic and time to change person.
          schedule(scan, 10000)
        } catch (err) {
          if (cancelled) return
          setError(err.message || 'Attendance request failed. Check the backend connection.')
          setRunning(false)
        }
      }
      await capture()
    }
    const start = async () => {
      try {
        if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
          throw new Error('Webcam attendance needs HTTPS or localhost and a supported browser.')
        }
        setError('')
        setStatus('Opening camera…')
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'user', width: { ideal: 960 }, height: { ideal: 720 } }, audio: false,
        })
        if (cancelled) { stream.getTracks().forEach((track) => track.stop()); return }
        videoRef.current.srcObject = stream
        await videoRef.current.play()
        await scan()
      } catch (err) {
        if (cancelled) return
        setError(err.name === 'NotAllowedError'
          ? 'Camera permission denied. Allow this website to use your camera, then start again.'
          : err.message || 'Cannot open camera. Close other apps using it and retry.')
        setRunning(false)
      }
    }
    start()
    return () => {
      cancelled = true
      clearTimeout(timer)
      controller.abort()
      stream?.getTracks().forEach((track) => track.stop())
      document.removeEventListener('visibilitychange', stopWhenHidden)
      setStatus('Camera off')
    }
  }, [running, bypass])

  return (
    <section className="panel" aria-label="Laptop webcam attendance">
      <div className="panel-head"><h2 className="panel-title">Laptop Webcam Attendance</h2></div>
      <p>Register each student in Members and enroll their face with consent first. Start the camera, then show one person at a time. Recognition records entry automatically.</p>
      <p>While running, face images are sent to your AAMS backend for recognition and evidence storage. Telegram entry messages use the private settings in Communicate.</p>
      <video ref={videoRef} muted playsInline aria-label="Live laptop camera"
        style={{ display: running ? 'block' : 'none', width: '100%', maxHeight: 420, background: '#111', borderRadius: 12 }} />
      <label style={{ display: 'block', margin: '12px 0' }}>
        <input type="checkbox" checked={bypass} disabled={running}
          onChange={(event) => setBypass(event.target.checked)} />{' '}
        Prototype demo: skip blink check (photos may be accepted)
      </label>
      <p role="status">{status}</p>
      {error && <div className="form-error" role="alert">{error}</div>}
      {IS_STATIC_DEMO && <p>Connect a live backend to enable webcam attendance.</p>}
      <button className={`btn ${running ? 'ghost' : 'primary'}`} type="button" disabled={IS_STATIC_DEMO}
        onClick={() => setRunning((value) => !value)}>{running ? 'Stop webcam attendance' : 'Start webcam attendance'}</button>
      <p style={{ fontSize: 12 }}>Stops when this page is hidden or closed. A request already accepted by the server may still finish after stopping.</p>
    </section>
  )
}
