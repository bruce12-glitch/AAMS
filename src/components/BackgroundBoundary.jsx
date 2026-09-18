import { Component } from 'react'

/**
 * Error boundaries.
 *
 * Two levels of containment, both added after a single runtime error in the
 * sidebar took the entire console down to a blank black page:
 *
 *   1. BackgroundBoundary — wraps the decorative WebGL scene only.
 *   2. AppBoundary        — the last line of defence, around the whole shell.
 *
 * The failure that motivated these was a ReferenceError (`<IconFace />` used
 * without an import) which Vite compiled happily and only threw at runtime,
 * unmounting the React tree. A boundary cannot fix a broken component, but it
 * can keep the rest of the application on screen and make the fault legible
 * instead of presenting the operator with a black rectangle.
 */

/** Contains failures from the decorative background scene. */
export class BackgroundBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { failed: false }
  }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  componentDidCatch(error) {
    // One concise line only. This is a cosmetic layer; don't spam the console.
    console.warn(
      '[AAMS] Background effect disabled (WebGL unavailable or chunk failed to load):',
      error?.message ?? error
    )
  }

  render() {
    if (this.state.failed) return null
    return this.props.children
  }
}

/**
 * Last-resort boundary around the entire console shell.
 *
 * If a page or shell component throws, we keep the frame visible and show a
 * readable error with a reload action, rather than unmounting to a blank
 * screen. The stack is logged in full so the fault can be diagnosed from the
 * browser console.
 */
export class AppBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    console.error('[AAMS] Console crashed:', error, info?.componentStack)
  }

  render() {
    const { error } = this.state
    if (!error) return this.props.children

    return (
      <div
        role="alert"
        style={{
          position: 'relative',
          zIndex: 10,
          minHeight: '100vh',
          display: 'grid',
          placeItems: 'center',
          padding: 24,
          textAlign: 'center'
        }}
      >
        <div style={{ maxWidth: 520 }}>
          <h1
            style={{
              fontFamily: "'Space Grotesk', system-ui, sans-serif",
              fontSize: 20,
              margin: '0 0 10px',
              color: '#111827'
            }}
          >
            Console error
          </h1>
          <p style={{ color: '#4b5563', fontSize: 13.5, lineHeight: 1.6, margin: '0 0 18px' }}>
            The interface hit an unexpected error and stopped rendering. The
            technical detail is in the browser console.
          </p>
          <pre
            style={{
              fontFamily: "'JetBrains Mono', ui-monospace, monospace",
              fontSize: 11.5,
              color: '#b91c1c',
              background: '#fef2f2',
              border: '1px solid #fecaca',
              borderRadius: 10,
              padding: '10px 12px',
              textAlign: 'left',
              overflowX: 'auto',
              whiteSpace: 'pre-wrap',
              margin: '0 0 18px'
            }}
          >
            {String(error?.message ?? error)}
          </pre>
          <button
            type="button"
            onClick={() => window.location.reload()}
            style={{
              fontFamily: 'inherit',
              fontSize: 13,
              fontWeight: 600,
              color: '#04060d',
              background: 'linear-gradient(135deg, #22d3ee 0%, #a78bfa 100%)',
              border: 'none',
              borderRadius: 999,
              padding: '9px 22px',
              cursor: 'pointer'
            }}
          >
            Reload console
          </button>
        </div>
      </div>
    )
  }
}

export default BackgroundBoundary
