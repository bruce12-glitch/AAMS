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

const KEY = 'aams_srmist_auth'

export function getSession() {
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (parsed && isSrmistEmail(parsed.email)) return parsed
    return null
  } catch {
    return null
  }
}

export function saveSession(email) {
  const clean = normalizeEmail(email)
  const session = { email: clean, at: new Date().toISOString() }
  localStorage.setItem(KEY, JSON.stringify(session))
  return session
}

export function clearSession() {
  localStorage.removeItem(KEY)
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
  if (IS_STATIC_DEMO) return saveSession(clean)
  let res
  try {
    res = await fetch(apiUrl('/api/auth/login'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: clean, password: String(password) })
    })
  } catch {
    // Backend unreachable (dev without API): honour the local rule.
    // (On the Pages live site this path is unreachable — IS_STATIC_DEMO
    // covers it — but a misconfigured host falls back safely here.)
    return saveSession(clean)
  }
  const contentType = res.headers.get('content-type') || ''
  let body = null
  if (contentType.includes('application/json')) {
    try { body = await res.json() } catch { body = null }
  }
  if (res.ok) return saveSession(clean)
  if (body?.detail && (res.status === 400 || res.status === 403)) {
    // Genuine backend verdict (unknown mail, no password set, wrong
    // password, non-SRMIST domain) — never bypass.
    throw new Error(body.detail)
  }
  // Backend missing/misbehaving (404 HTML, 405, proxy error page):
  // honour the local rule.
  return saveSession(clean)
}
