import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Two build modes:
//   dev / lab deployment  -> base '/', API proxied to the local FastAPI service
//   GitHub Pages (static) -> base './', no proxy, console runs on demo data
//
// The Pages workflow sets VITE_TARGET=pages. See PAGES_DEPLOY.md.
const isPages = process.env.VITE_TARGET === 'pages'

export default defineConfig({
  // Relative base so the bundle resolves under /<repo-name>/ on Pages.
  base: isPages ? './' : '/',
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
