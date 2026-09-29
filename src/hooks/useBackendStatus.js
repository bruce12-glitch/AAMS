import { useEffect, useRef, useState } from 'react'
import { IS_STATIC_DEMO } from '../config/runtime'
import { apiUrl } from '../api/client'

/**
 * Shared backend-connection signal for the shell (sidebar status pill).
 *
 * Pages each own their own usePolling instances, so there was no single
 * source of truth for "is the API up?" - the sidebar's isLive prop was
 * never passed and therefore always rendered "Demo Data", even when the
 * API was connected. This probes /health once on mount and then on an
 * interval, and reports a single boolean the shell can trust.
 *
 * /health is intentionally cheap and side-effect free (see app/main.py),
 * so polling it is safe and does not touch the CV engine.
 *
 * When VITE_TARGET=pages there is no backend by design; we skip probing
 * entirely and report offline so the console shows its demo state without
 * spamming 404s into the browser console.
 *
 * The flag lives in config/runtime.js so every data hook reads the same
 * value. Two separate `import.meta.env` reads would be fine too, but a
 * single source is easier to audit.
 */
export function useBackendStatus(intervalMs = 15000) {
  const [isLive, setIsLive] = useState(false)
  const mountedRef = useRef(true)

  useEffect(() => {
    if (IS_STATIC_DEMO) {
      // Static demo build: no API exists, don't generate network noise.
      setIsLive(false)
      return undefined
    }

    mountedRef.current = true

    async function probe() {
      try {
        const res = await fetch(apiUrl('/health'), { method: 'GET' })
        if (mountedRef.current) setIsLive(res.ok)
      } catch {
        if (mountedRef.current) setIsLive(false)
      }
    }

    probe()
    const id = setInterval(() => {
      if (document.visibilityState === 'visible') probe()
    }, intervalMs)

    return () => {
      mountedRef.current = false
      clearInterval(id)
    }
  }, [intervalMs])

  return isLive
}
