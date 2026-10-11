/**
 * SRMIST-only auth — single source of truth on the frontend.
 * ONLY @srmist.edu.in is accepted. Everything else is rejected locally
 * (and again server-side at /api/auth/login + enrollment).
 */

import { IS_STATIC_DEMO } from '../config/runtime'
import { apiUrl } from '../api/client'

export const SRMIST_SUFFIX = '@srmist.edu.in'

const SRMIST_RE = /^[a-z0-9._%+-]+@srmist\.edu\.in$/i

export function normalizeEmail(email) {
  return String(email ?? '').trim().toLowerCase()
}

export function isSrmistEmail(email) {
  return SRMIST_RE.test(normalizeEmail(email))
}

export const SESSION_KEY = 'aams_srmist_auth'

export function getSession() {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (!parsed || !isSrmistEmail(parsed.email)) return null
    if (!IS_STATIC_DEMO && (!parsed.token || Number(parsed.expires_at) * 1000 <= Date.now())) {
      clearSession()
      return null
    }
    return parsed
  } catch {
    return null
  }
}

export function saveSession(data) {
  const supplied = typeof data === 'string' ? { email: data } : data
  const session = {
    ...supplied,
    email: normalizeEmail(supplied?.email),
    at: new Date().toISOString()
  }
  sessionStorage.setItem(SESSION_KEY, JSON.stringify(session))
  // Remove pre-session builds that stored an email-only bypass persistently.
  localStorage.removeItem(SESSION_KEY)
  return session
}

export function clearSession() {
  sessionStorage.removeItem(SESSION_KEY)
  localStorage.removeItem(SESSION_KEY)
}

export const MIN_PASSWORD_LEN = 6

/**
 * Sign in with SRMIST email + member password.
 *
 * - Static demo build (no backend by design): requires an SRMIST address
 *   plus any password of MIN_PASSWORD_LEN+ chars, verified locally. The
 *   demo holds no real data, so this is a gate, not a proof.
 * - With a backend: the server verifies the password hash. A 400/403 with
 *   a JSON verdict is always rethrown — a wrong password must never fall
 *   back to local access. Only a missing/unreachable backend (404 HTML,
 *   network error) honours the local rule.
 */
export async function loginWithBackend(email, password) {
  const clean = normalizeEmail(email)
  if (!isSrmistEmail(clean)) {
    throw new Error(`Only ${SRMIST_SUFFIX} mail IDs are allowed`)
  }
  if (!password || String(password).length < MIN_PASSWORD_LEN) {
    throw new Error(`Password must be at least ${MIN_PASSWORD_LEN} characters`)
  }
  // Static demo build ships with no backend by design — skip the network
  // call entirely instead of failing on the 404 HTML fallback page.
  if (IS_STATIC_DEMO) return saveSession({ email: clean, role: 'admin', name: 'Demo Administrator' })
  let res
  try {
    res = await fetch(apiUrl('/api/auth/login'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: clean, password: String(password) })
    })
  } catch {
    throw new Error('The AAMS server is unavailable. Check the backend connection and try again.')
  }
  const contentType = res.headers.get('content-type') || ''
  let body = null
  if (contentType.includes('application/json')) {
    try { body = await res.json() } catch { body = null }
  }
  if (res.ok && body?.token) return saveSession(body)
  if (body?.detail) {
    // Genuine backend verdict (unknown mail, no password set, wrong
    // password, non-SRMIST domain) — never bypass.
    throw new Error(body.detail)
  }
  throw new Error(`Sign-in failed (${res.status}). Check the backend configuration.`)
}
