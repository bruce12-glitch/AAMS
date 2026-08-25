import { lazy, Suspense, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

const BackgroundScene = lazy(() => import('./three/BackgroundScene'))
import Sidebar, { NAV_ITEMS } from './components/Sidebar'
import TopBar from './components/TopBar'
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
  const Page = PAGES[page] ?? Dashboard
  const title = NAV_ITEMS.find((n) => n.id === page)?.label ?? 'Dashboard'

  return (
    <>
      <Suspense fallback={null}>
        <BackgroundScene />
      </Suspense>
      <div className="app-shell">
        <Sidebar active={page} onSelect={setPage} />
        <div className="main-col">
          <TopBar title={title} />
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
    </>
  )
}
