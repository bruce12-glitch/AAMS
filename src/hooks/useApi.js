import { useCallback, useEffect, useRef, useState } from 'react'
import { apiGet } from '../api/client'

/**
 * Polls a GET endpoint and falls back to mock data when the
 * backend is unreachable, so the UI always renders.
 *
 * @param path       API path, e.g. '/dashboard/stats'
 * @param fallback   Sample data used before the first response and whenever
 *                   the request fails. Pass a STABLE reference - a module
 *                   constant or a useMemo - not a fresh object literal per
 *                   render (see the fallbackRef note below).
 * @param intervalMs Poll cadence in milliseconds.
 * @param options.enabled  Set false to suppress polling entirely. Used by the
 *                   static Pages build, which has no backend: without this,
 *                   every mounted hook would fire a request that 404s and
 *                   flood the console with failed fetches.
 *
 * The `enabled` flag arrived as a bare 4th positional argument, which made
 * call sites read as `usePolling(path, fallback, 6000, false)` - the meaning
 * of the trailing boolean was invisible, and the 3rd argument could not be
 * omitted to reach it. An options object keeps call sites self-describing.
 */
export function usePolling(path, fallback, intervalMs = 8000, options = {}) {
  const { enabled = true } = options
  const [data, setData] = useState(fallback)
  const [isLive, setIsLive] = useState(false)
  const [loading, setLoading] = useState(enabled)
  const [error, setError] = useState(null)

  // Hold the latest fallback in a ref. Previously `fallback` was read inside
  // fetchOnce but omitted from its dependency list, so the closure captured
  // the first fallback forever - a stale-closure bug that would serve outdated
  // sample data even after the caller supplied a fresh object.
  const fallbackRef = useRef(fallback)
  fallbackRef.current = fallback

  // Track mount state per-effect rather than with a single mutable ref, so a
  // remount cannot leave a previously-unmounted component marked as mounted.
  const mountedRef = useRef(true)

  const fetchOnce = useCallback(async (silent = false) => {
    if (!enabled) return
    if (!silent) setLoading(true)
    try {
      const res = await apiGet(path)
      if (!mountedRef.current) return
      setData(res)
      setIsLive(true)
      setError(null)
    } catch (err) {
      if (!mountedRef.current) return
      setIsLive(false)
      setError(err?.message ?? 'unreachable')
      if (fallbackRef.current !== undefined) setData(fallbackRef.current)
    } finally {
      if (mountedRef.current) setLoading(false)
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
      clearInterval(id)
    }
  }, [fetchOnce, intervalMs, enabled])

  // refresh() is exposed to callers as a stable callback so it can be used in
  // dependency arrays without re-running every render.
  const refresh = useCallback(() => fetchOnce(true), [fetchOnce])

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
