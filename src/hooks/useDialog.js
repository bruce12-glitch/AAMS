import { useEffect, useRef } from 'react'

/**
 * Behaviour every overlay in this console needs, in one place.
 *
 * Two dialogs already existed (Enroll, QR Pass) and neither announced
 * itself, moved focus, or could be dismissed with Escape. Duplicating the
 * fix into each would guarantee the third one misses it, so it lives here.
 *
 * Attach the returned ref to the element carrying `role="dialog"`, and
 * that element should also set `aria-modal="true"` and
 * `aria-labelledby` pointing at its title.
 *
 *   const ref = useDialog(open, onClose)
 *   <div ref={ref} role="dialog" aria-modal="true" aria-labelledby={titleId}>
 *
 * What it does:
 *   - moves focus to the first control on open (or the dialog itself if it
 *     has none), so keyboard users are not left typing into the page
 *     behind the overlay
 *   - returns focus to whatever opened it on close, not to <body>
 *   - Escape dismisses
 *   - Tab cycles within the dialog, so focus cannot escape behind it
 */
const FOCUSABLE = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])'
].join(', ')

export function useDialog(open, onClose) {
  const ref = useRef(null)
  const lastFocused = useRef(null)

  // Held in a ref so the keydown effect below depends only on `open`.
  // Otherwise a caller passing an inline arrow re-attaches the listener on
  // every render.
  const onCloseRef = useRef(onClose)
  onCloseRef.current = onClose

  useEffect(() => {
    if (!open) return
    lastFocused.current = document.activeElement
    const node = ref.current
    const first = node?.querySelector(FOCUSABLE)
    ;(first ?? node)?.focus()

    return () => {
      const prev = lastFocused.current
      // The opener can be gone by now (e.g. the row that opened the QR
      // dialog was filtered out) — focus would then land on <body>.
      if (prev && typeof prev.focus === 'function' && document.contains(prev)) {
        prev.focus()
      }
    }
  }, [open])

  useEffect(() => {
    if (!open) return

    const onKeyDown = (e) => {
      if (e.key === 'Escape') {
        e.stopPropagation()
        onCloseRef.current?.()
        return
      }
      if (e.key !== 'Tab') return

      const node = ref.current
      if (!node) return
      const focusables = node.querySelectorAll(FOCUSABLE)
      if (!focusables.length) return

      const first = focusables[0]
      const last = focusables[focusables.length - 1]
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault()
        last.focus()
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault()
        first.focus()
      }
    }

    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [open])

  return ref
}

export default useDialog
