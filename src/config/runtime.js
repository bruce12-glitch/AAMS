/**
 * Runtime mode flags.
 *
 * VITE_TARGET=pages produces a static demo build. On its own it has no
 * backend: data hooks skip network calls entirely instead of relying on
 * failures being caught, which keeps the browser console clean and the
 * demo unambiguous.
 *
 * VITE_API_URL links the site to a real backend + database (e.g. the lab
 * API hosted for the team). When set — in any build — the console talks
 * to that backend, so IS_STATIC_DEMO flips off and every feature
 * (enrollment, login verification, Telegram, live data) goes live:
 *
 *   VITE_API_URL=https://<your-api-host> npm run build
 */
export const API_URL = (import.meta.env.VITE_API_URL ?? '').replace(/\/+$/, '')

export const IS_STATIC_DEMO =
  import.meta.env.VITE_TARGET === 'pages' && API_URL === ''

/** Base path the console is served from, for building absolute links. */
export const BASE_PATH = import.meta.env.BASE_URL ?? '/'
