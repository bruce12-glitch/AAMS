import { useEffect, useRef, useState } from 'react'

/**
 * Animated count-up. Jumps instantly if the user prefers reduced motion.
 */
export function useCountUp(target, durationMs = 900) {
  const [value, setValue] = useState(0)
  const fromRef = useRef(0)
  const rafRef = useRef(0)

  useEffect(() => {
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const from = fromRef.current

    if (reduced || !Number.isFinite(target)) {
      setValue(Number.isFinite(target) ? target : 0)
      fromRef.current = Number.isFinite(target) ? target : 0
      return undefined
    }

    const start = performance.now()
    const tick = (t) => {
      const p = Math.min((t - start) / durationMs, 1)
      const eased = 1 - Math.pow(1 - p, 3)
      const next = from + (target - from) * eased
      setValue(next)
      if (p < 1) {
        rafRef.current = requestAnimationFrame(tick)
      } else {
        fromRef.current = target
      }
    }
    rafRef.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(rafRef.current)
  }, [target, durationMs])

  return Math.round(value)
}
