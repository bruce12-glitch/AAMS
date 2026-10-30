import { useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'

/** Secure-context webcam capture used by enrollment and entry testing. */
export default function CameraCapture({ open, maxShots = 1, burst = false, onDone, onClose }) {
  const videoRef = useRef(null)
  const streamRef = useRef(null)
  const timerRef = useRef(null)
  const [shots, setShots] = useState([])
  const [error, setError] = useState('')
  const [ready, setReady] = useState(false)
  const [capturing, setCapturing] = useState(false)

  useEffect(() => {
    if (!open) return undefined
    let cancelled = false
    const start = async () => {
      setShots([])
      setError('')
      setReady(false)
      setCapturing(false)
      try {
        if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
          throw new Error('Camera capture needs HTTPS or localhost in a supported browser.')
        }
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } },
          audio: false
        })
        if (cancelled) return stream.getTracks().forEach((track) => track.stop())
        streamRef.current = stream
        if (videoRef.current) {
          videoRef.current.srcObject = stream
          await videoRef.current.play()
          if (!cancelled) setReady(true)
        }
      } catch (err) {
        setError(err?.name === 'NotAllowedError'
          ? 'Camera permission was denied. Allow camera access or upload a photo instead.'
          : err.message || 'Could not open the webcam. Check that another app is not using it.')
      }
    }
    start()
    return () => {
      cancelled = true
      clearTimeout(timerRef.current)
      streamRef.current?.getTracks().forEach((track) => track.stop())
      streamRef.current = null
    }
  }, [open])

  const capture = () => {
    const video = videoRef.current
    if (!video?.videoWidth) return setError('Camera is still starting — try again in a moment.')
    setError('')
    setCapturing(true)
    const captured = []
    const take = () => {
      try {
        const canvas = document.createElement('canvas')
        const scale = Math.min(1, 1280 / Math.max(video.videoWidth, video.videoHeight))
        canvas.width = Math.round(video.videoWidth * scale)
        canvas.height = Math.round(video.videoHeight * scale)
        canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height)
        const uri = canvas.toDataURL('image/jpeg', 0.92)
        captured.push(uri)
        if (burst) {
          setShots([...captured])
          if (captured.length < maxShots) { timerRef.current = setTimeout(take, 250); return }
        } else { setShots((current) => [...current, uri].slice(-maxShots)) }
      } catch { setError('Could not capture a camera frame. Retake after the preview starts.') }
      setCapturing(false)
    }
    take()
  }

  const finish = () => {
    if (!shots.length) return setError('Capture at least one clear face photo.')
    onDone?.(shots)
    onClose?.()
  }

  return (
    <AnimatePresence>
      {open && (
        <motion.div className="modal-backdrop" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
          <motion.div className="modal" role="dialog" aria-modal="true" aria-label="Webcam capture"
            initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.97 }}>
            <h3 className="modal-title">Camera Capture</h3>
            <p className="modal-sub">{burst ? 'Press Capture, then blink naturally during the short sequence. Keep the same person in view.' : 'Face the camera in even light. Keep your full face visible and still.'}</p>
            <video ref={videoRef} muted playsInline
              style={{ width: '100%', maxHeight: 420, borderRadius: 12, background: '#111', objectFit: 'cover' }} />
            {shots.length > 0 && (
              <div className="preview-row" style={{ marginTop: 10 }}>
                {shots.map((shot, index) => <img src={shot} alt={`camera shot ${index + 1}`} key={index} />)}
                <span>{shots.length}/{maxShots} captured</span>
              </div>
            )}
            {error && <div className="form-error" role="alert">{error}</div>}
            <div className="modal-actions">
              <button className="btn ghost" type="button" onClick={onClose}>Cancel</button>
              {shots.length > 0 && <button className="btn ghost" type="button" disabled={capturing} onClick={() => setShots([])}>Retake</button>}
              <button className="btn primary" type="button" onClick={capture}
                disabled={!ready || capturing || shots.length >= maxShots}>{capturing ? 'Capturing… blink now' : 'Capture'} {maxShots > 1 ? `(${shots.length}/${maxShots})` : ''}</button>
              <button className="btn primary" type="button" onClick={finish} disabled={capturing || !shots.length}>{burst ? 'Use sequence' : `Use photo${shots.length === 1 ? '' : 's'}`}</button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
