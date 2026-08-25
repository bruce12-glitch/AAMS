import { motion } from 'framer-motion'
import { IconGauge, IconScan, IconList, IconBell, IconUsers, IconReport } from './icons'

export const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard', icon: IconGauge, section: 'Overview' },
  { id: 'live', label: 'Live Monitor', icon: IconScan, section: 'Operations' },
  { id: 'logs', label: 'Entry Logs', icon: IconList, section: 'Operations' },
  { id: 'alerts', label: 'Alerts', icon: IconBell, section: 'Operations' },
  { id: 'users', label: 'Members', icon: IconUsers, section: 'Admin' },
  { id: 'reports', label: 'Reports', icon: IconReport, section: 'Admin' }
]

export default function Sidebar({ active, onSelect, isLive }) {
  let lastSection = null

  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-logo">
          <IconFace width={20} height={20} />
        </div>
        <div>
          <div className="brand-name">FacePass</div>
          <div className="brand-sub">FabLab · AAMS</div>
        </div>
      </div>

      <nav>
        {NAV_ITEMS.map(({ id, label, icon: Icon, section }) => {
          const header = section !== lastSection ? section : null
          lastSection = section
          return (
            <div key={id}>
              {header && <div className="nav-section-label">{header}</div>}
              <button
                className={`nav-item ${active === id ? 'active' : ''}`}
                onClick={() => onSelect(id)}
                type="button"
              >
                {active === id && (
                  <motion.span
                    layoutId="nav-indicator"
                    className="nav-indicator"
                    transition={{ type: 'spring', stiffness: 420, damping: 34 }}
                  />
                )}
                <span className="nav-glyph"><Icon width={17} height={17} /></span>
                {label}
              </button>
            </div>
          )
        })}
      </nav>

      <div className="sidebar-footer">
        <span className="conn-pill">
          <span className={`conn-dot ${isLive ? 'live' : 'demo'}`} />
          {isLive ? 'API Connected' : 'Demo Data'}
        </span>
      </div>
    </aside>
  )
}
