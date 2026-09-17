/**
 * Runtime mode flags.
 *
 * VITE_TARGET=pages produces a static demo build with no backend: every
 * request would 404. Importing this flag lets data hooks skip network calls
 * entirely instead of relying on failures being caught, which keeps the
 * browser console clean and the demo unambiguous.
 */
export const IS_STATIC_DEMO = import.meta.env.VITE_TARGET === 'pages'

/** Base path the console is served from, for building absolute links. */
export const BASE_PATH = import.meta.env.BASE_URL ?? '/'
