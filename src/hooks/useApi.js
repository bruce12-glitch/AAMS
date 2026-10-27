import { useCallback, useEffect, useRef, useState } from 'react'
import { apiGet } from '../api/client'
import { IS_STATIC_DEMO } from '../config/runtime'

/** Poll current API data, keep the last real response on failure, and prevent
 * overlapping or obsolete requests from overwriting the current page. Sample
 * records are only used by an explicitly static demonstration build. */
export function usePolling(path, fallback, intervalMs = 8000, options = {}) {
  const { enabled = true } = options
  const [data, setData] = useState(IS_STATIC_DEMO ? fallback : null)
  const [isLive, setIsLive] = useState(false)
  const [loading, setLoading] = useState(enabled)
  const [error, setError] = useState(null)

  // Track mount state per-effect rather than with a single mutable ref, so a
  // remount cannot leave a previously-unmounted component marked as mounted.
  const mountedRef = useRef(true)
  const requestRef = useRef(0)
  const inFlightRef = useRef(false)

  const fetchOnce = useCallback(async (silent = false, force = false) => {
    if (!enabled || (inFlightRef.current && !force)) return
    inFlightRef.current = true
    const requestId = ++requestRef.current
    if (!silent) setLoading(true)
    try {
      const res = await apiGet(path)
      if (!mountedRef.current || requestId !== requestRef.current) return
      setData(res)
      setIsLive(true)
      setError(null)
    } catch (err) {
      if (!mountedRef.current || requestId !== requestRef.current) return
      setIsLive(false)
      setError(err?.message ?? 'unreachable')
      // Keep the last real response on failure; never substitute sample records.
    } finally {
      if (requestId === requestRef.current) {
        inFlightRef.current = false
        if (mountedRef.current) setLoading(false)
      }
    }
  }, [path, enabled])

  useEffect(() => {
    if (!enabled) {
      // No backend by design (static demo): stay in demo state, don't poll,
      // and don't emit failed requests into the browser console.
      setLoading(false)
      setIsLive(false)
      return undefined
    }
    mountedRef.current = true
    fetchOnce(false)
    const id = setInterval(() => {
      if (document.visibilityState === 'visible') fetchOnce(true)
    }, intervalMs)
    return () => {
      mountedRef.current = false
      requestRef.current += 1
      inFlightRef.current = false
      clearInterval(id)
    }
  }, [fetchOnce, intervalMs, enabled])

  // refresh() is exposed to callers as a stable callback so it can be used in
  // dependency arrays without re-running every render.
  // An explicit refresh after a mutation supersedes an older in-flight poll;
  // its stale response must not undo the status the server just saved.
  const refresh = useCallback(() => fetchOnce(true, true), [fetchOnce])

  return { data, isLive, loading, error, refresh }
}

/** Ticking clock for the topbar. */
export function useClock() {
  const [now, setNow] = useState(() => new Date())
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(id)
  }, [])
  return now
}
