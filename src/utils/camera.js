/** Best-effort hardware focus/exposure; never promise unsupported controls. */
export async function configureCamera(stream) {
  const track = stream?.getVideoTracks?.()[0]
  try {
    const capabilities = track?.getCapabilities?.() || {}
    const controls = {}
    if (capabilities.focusMode?.includes('continuous')) controls.focusMode = 'continuous'
    if (capabilities.exposureMode?.includes('continuous')) controls.exposureMode = 'continuous'
    if (Object.keys(controls).length) await track.applyConstraints({ advanced: [controls] })
  } catch {
    // Browsers/cameras may advertise controls they cannot apply. Capture must
    // still work; backend face-quality checks remain the source of truth.
  }
}

export const CAMERA_SETTLE_MS = 1500

export function nextScanDelay(result) {
  // Do not wait another ten seconds to recover from an ordinary soft frame.
  // Requests remain sequential; successful/unknown-person scans keep cooldown.
  return ['quality', 'noface', 'liveness', 'ambiguous'].includes(result.tag) ? 2000 : 10000
}
