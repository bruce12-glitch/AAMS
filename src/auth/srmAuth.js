/**
 * SRMIST-only auth — single source of truth on the frontend.
 * ONLY @srmist.edu.in is accepted. Everything else is rejected locally
 * (and again server-side at /api/auth/login + enrollment).
 */

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

/** Validate against the backend too — falls back to local rule offline. */
export async function loginWithBackend(email) {
  const clean = normalizeEmail(email)
  if (!isSrmistEmail(clean)) {
    throw new Error(`Only ${SRMIST_SUFFIX} mail IDs are allowed`)
  }
  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: clean })
    })
    if (!res.ok) {
      let detail = `Only ${SRMIST_SUFFIX} mail IDs are allowed`
      try {
        const body = await res.json()
        if (body?.detail) detail = body.detail
      } catch { /* keep default */ }
      throw new Error(detail)
    }
    return saveSession(clean)
  } catch (err) {
    // Backend offline (static demo / dev without API): honour the local
    // rule so the console stays usable. Server re-checks on every real call.
    if (err instanceof TypeError) return saveSession(clean)
    throw err
  }
}
