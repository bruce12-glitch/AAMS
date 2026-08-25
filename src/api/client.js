const BASE = '/api'

async function request(path, options = {}, timeoutMs = 7000) {
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
        if (body?.detail) detail = String(body.detail)
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

export function toArray(payload, key) {
  if (!payload) return []
  if (Array.isArray(payload)) return payload
  if (Array.isArray(payload[key])) return payload[key]
  for (const k of Object.keys(payload)) {
    if (Array.isArray(payload[k])) return payload[k]
  }
  return []
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
