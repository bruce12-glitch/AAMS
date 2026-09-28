/**
 * SRMIST-only auth — single source of truth on the frontend.
 * ONLY @srmist.edu.in is accepted. Everything else is rejected locally
 * (and again server-side at /api/auth/login + enrollment).
 */

import { IS_STATIC_DEMO } from '../config/runtime'

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

/**
 * Validate against the backend too — falls back to the local rule whenever
 * there is no usable backend (static Pages demo, dev without API).
 *
 * Why the fallback is broad: on GitHub Pages /api/* answers 404 with an
 * HTML body, and res.json() on HTML throws a SyntaxError (not a TypeError).
 * Treating only TypeError as "offline" rejected VALID @srmist.edu.in mail
 * IDs on the live site. Only an explicit backend 403 is a real rejection —
 * everything else honours the local rule (the server re-checks on every
 * real API call anyway).
 */
export async function loginWithBackend(email) {
  const clean = normalizeEmail(email)
  if (!isSrmistEmail(clean)) {
    throw new Error(`Only ${SRMIST_SUFFIX} mail IDs are allowed`)
  }
  // Static demo build ships with no backend by design — skip the network
  // call entirely instead of failing on the 404 HTML fallback page.
  if (IS_STATIC_DEMO) return saveSession(clean)
  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: clean })
    })
    const contentType = res.headers.get('content-type') || ''
    let body = null
    if (contentType.includes('application/json')) {
      try { body = await res.json() } catch { body = null }
    }
    if (res.status === 403) {
      const rejection = new Error(body?.detail || `Only ${SRMIST_SUFFIX} mail IDs are allowed`)
      rejection.isAuthRejection = true
      throw rejection
    }
    // res.ok, or backend missing/misbehaving (404 HTML, 405, non-JSON):
    // honour the local SRMIST rule. Genuine API calls re-validate server-side.
    return saveSession(clean)
  } catch (err) {
    // A real backend 403 verdict stays rejected; everything else
    // (offline, HTML fallback page, proxy error) falls back to local.
    if (err?.isAuthRejection) throw err
    return saveSession(clean)
  }
}
