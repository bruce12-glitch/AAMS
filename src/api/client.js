const BASE = '/api'

const ADMIN_KEY = 'aams_admin_token'

export function getAdminToken() {
  return localStorage.getItem(ADMIN_KEY) ?? ''
}

export function setAdminToken(token) {
  localStorage.setItem(ADMIN_KEY, String(token ?? '').trim())
}

function adminHeaders() {
  const h = { 'Content-Type': 'application/json' }
  const t = getAdminToken()
  if (t) h['X-Admin-Token'] = t
  return h
}

async function request(path, options = {}, timeoutMs = 15000) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  try {
    const res = await fetch(BASE + path, {
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
      ...options
    })
    if (!res.ok) {
      let detail = `${res.status} ${res.statusText}`
      try {
        const body = await res.json()
        if (body?.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
      } catch { /* non-json error body */ }
      throw new Error(detail)
    }
    return await res.json()
  } finally {
    clearTimeout(timer)
  }
}

export function apiGet(path, timeoutMs) {
  return request(path, { method: 'GET' }, timeoutMs)
}

export function apiPost(path, body, timeoutMs) {
  return request(path, { method: 'POST', body: JSON.stringify(body ?? {}) }, timeoutMs)
}

/** POST carrying the admin token header (mutating endpoints). */
export function adminPost(path, body, timeoutMs) {
  return request(path, { method: 'POST', headers: adminHeaders(), body: JSON.stringify(body ?? {}) }, timeoutMs)
}

export function apiPut(path, body, timeoutMs) {
  return request(path, { method: 'PUT', headers: adminHeaders(), body: JSON.stringify(body ?? {}) }, timeoutMs)
}

export function apiDelete(path, timeoutMs) {
  return request(path, { method: 'DELETE', headers: adminHeaders() }, timeoutMs)
}

export function toArray(payload, key) {
  if (!payload) return []
  if (Array.isArray(payload)) return payload
  if (Array.isArray(payload[key])) return payload[key]
  for (const k of Object.keys(payload)) {
    if (Array.isArray(payload[k])) return payload[k]
  }
  return []
}

/** Convert a File to a base64 data-URI (downscaling huge photos). */
export function fileToDataUri(file, maxDim = 1280) {
  return new Promise((resolve, reject) => {
    if (!file.type?.startsWith('image/')) {
      return reject(new Error(`${file.name || 'file'} is not an image`))
    }
    if (file.size > 8 * 1024 * 1024) {
      return reject(new Error(`${file.name || 'file'} exceeds 8 MB`))
    }
    const reader = new FileReader()
    reader.onerror = () => reject(new Error(`Could not read ${file.name || 'file'}`))
    reader.onload = () => {
      const img = new Image()
      img.onerror = () => reject(new Error(`Could not decode ${file.name || 'file'}`))
      img.onload = () => {
        try {
          const scale = Math.min(1, maxDim / Math.max(img.width, img.height))
          if (scale >= 1) return resolve(reader.result)
          const canvas = document.createElement('canvas')
          canvas.width = Math.round(img.width * scale)
          canvas.height = Math.round(img.height * scale)
          canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height)
          resolve(canvas.toDataURL('image/jpeg', 0.9))
        } catch (err) {
          reject(err)
        }
      }
      img.src = reader.result
    }
    reader.readAsDataURL(file)
  })
}

export const SIM_SCENARIOS = {
  authorized: { decision: 'GRANTED', tag: 'authorized', reason: 'Authorized entry' },
  proxy: { decision: 'DENIED', tag: 'proxy', reason: 'Proxy attempt detected' },
  unpaid: { decision: 'DENIED', tag: 'unpaid', reason: 'Payment expired' },
  unknown: { decision: 'DENIED', tag: 'unknown', reason: 'Unknown person' },
  spoof: { decision: 'DENIED', tag: 'spoof', reason: 'Spoof detected' },
  tailgate: { decision: 'GRANTED', tag: 'tailgate', reason: 'Multiple faces detected' }
}

export async function simulateEntry(scenario) {
  try {
    const res = await apiPost('/entry/simulate', { scenario }, 4000)
    return { ...res, source: 'api' }
  } catch {
    const local = SIM_SCENARIOS[scenario] ?? {
      decision: 'DENIED',
      tag: 'unknown',
      reason: 'Unknown scenario'
    }
    return { ...local, source: 'local' }
  }
}
