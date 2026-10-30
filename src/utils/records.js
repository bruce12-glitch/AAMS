import { parseTimestamp, LAB_TIME_ZONE } from './time.js'

const SOURCES = { snapshot: 'Uploaded / manual photo', webcam: 'Browser webcam', door_camera: 'Door camera', system: 'System event', legacy: 'Older · source unrecorded', sample: 'Demo data' }
const RESULTS = { authorized: 'Entry granted', proxy: 'Pass and face differ', unpaid: 'Payment blocks entry', unknown: 'No enrolled face matched', noface: 'No face detected', quality: 'Photo quality failed', token: 'Pass not valid', setup: 'Enrollment required', liveness: 'Liveness not verified', spoof: 'Liveness check failed', tailgate: 'Multiple faces detected' }

export const sourceLabel = (source) => SOURCES[source] || 'Source not recorded'
export const historyCount = (counts = {}) => (counts.legacy || 0) + (counts.sample || 0)
export const resultLabel = (value) => RESULTS[String(value || '').toLowerCase()] || String(value || 'Result not recorded').replaceAll('_', ' ')
export const decisionLabel = (value) => ({ GRANTED: 'Granted', DENIED: 'Denied' }[value] || 'Not recorded')
export const alertTitle = (value) => resultLabel(String(value || '').toLowerCase().replace(/_alert$/, ''))
export const paymentLabel = (value) => value ? String(value).replaceAll('_', ' ') : 'Not evaluated'

export function matchScore(row) {
  if (row.event_source === 'sample') return 'Demo value'
  if (row.comparison_performed === false || row.comparison_performed === 0) return 'Not compared'
  if (row.comparison_performed !== true && row.comparison_performed !== 1) return 'Not recorded'
  return Number.isFinite(row.similarity) ? row.similarity.toFixed(3) : 'Not recorded'
}

export function formatEventTime(value) {
  const date = parseTimestamp(value)
  return Number.isNaN(date.getTime()) ? 'Time not recorded' : date.toLocaleString('en-IN', {
    timeZone: LAB_TIME_ZONE, day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit',
  }) + ' IST'
}

// Display-only correction for legacy UTF-8 text decoded as Windows-1252.
// The stored original is preserved; never rewrite historical evidence here.
export const readableText = (value) => String(value || '').replaceAll('â€”', '—').replaceAll('â€“', '–').replaceAll('â€™', '’').replaceAll('Â§', '§')
