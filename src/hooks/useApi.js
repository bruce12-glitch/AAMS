import { useCallback, useEffect, useRef, useState } from 'react'
import { apiGet } from '../api/client'

/**
 * Polls a GET endpoint and falls back to mock data when the
 * backend is unreachable, so the UI always renders.
 */
export function usePolling(path, fallback, intervalMs = 8000) {
  const [data, setData] = useState(fallback)
  const [isLive, setIsLive] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const mountedRef = useRef(true)

  const fetchOnce = useCallback(async (silent = false) => {
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
      if (fallback !== undefined) setData(fallback)
    } finally {
      if (mountedRef.current) setLoading(false)
    }
  }, [path])

  useEffect(() => {
    mountedRef.current = true
    fetchOnce(false)
    const id = setInterval(() => {
      if (document.visibilityState === 'visible') fetchOnce(true)
    }, intervalMs)
    return () => {
      mountedRef.current = false
      clearInterval(id)
    }
  }, [fetchOnce, intervalMs])

  return { data, isLive, loading, error, refresh: () => fetchOnce(true) }
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
