/**
 * SRMIST-only auth — single source of truth on the frontend.
 * ONLY @srmist.edu.in is accepted. Everything else is rejected locally
 * (and again server-side at /api/auth/login + enrollment).
 */

import { IS_STATIC_DEMO } from '../config/runtime'
import { apiUrl } from '../api/client'

export const SRMIST_SUFFIX = '@srmist.edu.in'
export const AUTH_POLICY_VERSION = 'srmist-shared-password-v1'

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
    if (
      !parsed ||
      !isSrmistEmail(parsed.email) ||
      parsed.auth_policy !== AUTH_POLICY_VERSION
    ) {
      clearSession()
      return null
    }
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
    auth_policy: AUTH_POLICY_VERSION,
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

/**
 * Sign in with SRMIST email + the exact shared AAMS password.
 *
 * - Static builds never verify passwords in public browser code. They stay
 *   locked until VITE_API_URL connects the Pages build to the secure backend.
 * - With a backend: the server verifies the shared password. A 400/403 with
 *   a JSON verdict is always rethrown — a wrong password must never fall
 *   back to local access. An unreachable backend also fails closed.
 */
export async function loginWithBackend(email, password) {
  const clean = normalizeEmail(email)
  if (!isSrmistEmail(clean)) {
    throw new Error(`Only ${SRMIST_SUFFIX} mail IDs are allowed`)
  }
  if (!password) throw new Error('AAMS access password is required')
  if (IS_STATIC_DEMO) {
    throw new Error('Secure login is unavailable until the AAMS backend is connected')
  }
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
