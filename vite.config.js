import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Two build modes:
//   dev / lab deployment  -> base '/', API proxied to the local FastAPI service
//   GitHub Pages (static) -> base '/AAMS/', no proxy, console runs on demo data
//
// BASE PATH: on Pages the site is served from /AAMS/ (a project site), not
// from the domain root. This MUST be an absolute path, not './'.
//
// A relative './' base breaks deep links: the SPA fallback (404.html) is
// served for /AAMS/alerts, and the browser then resolves './assets/x.js'
// against /AAMS/alerts/ -> /AAMS/alerts/assets/x.js -> 404 -> blank page.
// An absolute '/AAMS/' base resolves correctly from any route depth.
//
// The workflow sets VITE_TARGET=pages. See PAGES_DEPLOY.md.
const isPages = process.env.VITE_TARGET === 'pages'

// Project-site base. Rename this if the repository is ever renamed.
const PAGES_BASE = '/AAMS/'

export default defineConfig({
  base: isPages ? PAGES_BASE : '/',
  plugins: [react()],
  server: {
    port: 3000,
    open: false,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
