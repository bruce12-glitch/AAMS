import { lazy, Suspense, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

const BackgroundScene = lazy(() => import('./three/BackgroundScene'))
import Sidebar, { NAV_ITEMS } from './components/Sidebar'
import TopBar from './components/TopBar'
import BackgroundBoundary, { AppBoundary } from './components/BackgroundBoundary'
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

export default function App() {
  const [page, setPage] = useState('dashboard')
  // Single shared connection signal for the shell; previously isLive was
  // never passed to Sidebar, so the status pill always read "Demo Data".
  const isLive = useBackendStatus()
  const Page = PAGES[page] ?? Dashboard
  const title = NAV_ITEMS.find((n) => n.id === page)?.label ?? 'Dashboard'

  return (
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
        <Sidebar active={page} onSelect={setPage} isLive={isLive} />
        <div className="main-col">
          <TopBar title={title} isLive={isLive} />
          <main className="page-scroll">
            <AnimatePresence mode="wait">
              <motion.div
                key={page}
                initial={{ opacity: 0, y: 14 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
              >
                <Page onNavigate={setPage} />
              </motion.div>
            </AnimatePresence>
          </main>
        </div>
      </div>
    </AppBoundary>
  )
}
