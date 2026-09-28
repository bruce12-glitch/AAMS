import { lazy, Suspense, useCallback, useEffect, useState } from 'react'
import { motion, AnimatePresence, MotionConfig } from 'framer-motion'

const BackgroundScene = lazy(() => import('./three/BackgroundScene'))
import Sidebar, { NAV_ITEMS } from './components/Sidebar'
import TopBar from './components/TopBar'
import Login from './components/Login'
import BackgroundBoundary, { AppBoundary } from './components/BackgroundBoundary'
import { InstitutionalLogos } from './components/Logo'
import { useAuth } from './auth/AuthContext'
import { useBackendStatus } from './hooks/useBackendStatus'
import Dashboard from './pages/Dashboard'
import LiveMonitor from './pages/LiveMonitor'
import Logs from './pages/Logs'
import Alerts from './pages/Alerts'
import Users from './pages/Users'
import Reports from './pages/Reports'

const PAGES = {
  dashboard: Dashboard,
  live: LiveMonitor,
  logs: Logs,
  alerts: Alerts,
  users: Users,
  reports: Reports
}

/** Read the initial page from the URL hash, e.g. #/live. */
function pageFromHash() {
  const raw = window.location.hash.replace(/^#\/?/, '')
  return raw in PAGES ? raw : 'dashboard'
}

export default function App() {
  const { isAuthed } = useAuth()
  const [page, setPage] = useState(pageFromHash)

  // Sync the URL with the current page, and react to back/forward.
  //
  // Navigation used to be pure React state, so a refresh always dumped you
  // back on the Dashboard and no page had a shareable URL. Hash routing needs
  // no server cooperation — important here, because this build is served as
  // static files where a history-route would 404 on refresh.
  useEffect(() => {
    const onHashChange = () => setPage(pageFromHash())
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  const navigate = useCallback((next) => {
    setPage(next)
    const target = `#/${next}`
    if (window.location.hash !== target) window.location.hash = target
  }, [])

  // Single shared connection signal for the shell; previously isLive was
  // never passed to Sidebar, so the status pill always read "Demo Data".
  const isLive = useBackendStatus()
  const Page = PAGES[page] ?? Dashboard
  const title = NAV_ITEMS.find((n) => n.id === page)?.label ?? 'Dashboard'

  // SRMIST gate: nothing inside the console renders until a valid
  // @srmist.edu.in session exists. Keeps the auth rule unmissable and
  // means every feature behind here is already operating as an authed user.
  if (!isAuthed) {
    return (
      <MotionConfig reducedMotion="user">
        <AppBoundary>
          <BackgroundBoundary>
            <Suspense fallback={null}>
              <BackgroundScene />
            </Suspense>
          </BackgroundBoundary>
          <Login />
        </AppBoundary>
      </MotionConfig>
    )
  }

  return (
    /* reducedMotion="user" makes every framer-motion animation in the tree
       honour the OS "reduce motion" setting. The CSS block in global.css
       only neutralises CSS transitions/animations — framer-motion drives
       its animations from JS and ignored the preference entirely, so
       reduced-motion users still got the full route transition, the
       staggered stat cards and the animated table rows. One wrapper here
       covers all 11 components that use motion. */
    <MotionConfig reducedMotion="user">
      <AppBoundary>
      {/* Decorative only. The boundary must sit INSIDE Suspense's sibling
          position so a failed chunk or missing WebGL cannot unmount the app.
          Previously this was a bare Suspense with fallback={null} and no
          boundary: any throw inside BackgroundScene blanked the whole page. */}
      <BackgroundBoundary>
        <Suspense fallback={null}>
          <BackgroundScene />
        </Suspense>
      </BackgroundBoundary>
      <div className="app-shell">
        <header className="institutional-header">
          <InstitutionalLogos />
        </header>
        <Sidebar active={page} onSelect={navigate} isLive={isLive} />
        <div className="main-col">
          <TopBar title={title} isLive={isLive} />
          <main className="page-scroll">
            <AnimatePresence mode="wait">
              <motion.div
                key={page}
                initial={{ opacity: 0, y: 14 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.32, ease: [0.22, 1, 0.36, 1] }}
              >
                <Page onNavigate={navigate} />
              </motion.div>
            </AnimatePresence>
          </main>
        </div>
      </div>
      </AppBoundary>
    </MotionConfig>
  )
}
