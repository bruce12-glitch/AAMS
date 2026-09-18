import { motion } from 'framer-motion'
import { IconGauge, IconScan, IconList, IconBell, IconUsers, IconReport } from './icons'
import { LogoLockup } from './Logo'

const CONTACT = {
  location: 'Fablab, Near Clock Tower, Annexure Campus, SRMIST, Potheri',
  city: 'Chennai, Tamil Nadu 603203, India',
  hours: 'Mon – Fri, 10:00 AM – 06:00 PM',
  email: 'fablab@srmist.edu.in',
  phone: '+91 79048 33702'
}

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
        <LogoLockup markSize={34} />
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
        <div className="contact-card">
          <h4 className="contact-title">Get in touch</h4>
          <p className="contact-hours">{CONTACT.hours}</p>

          <div className="contact-row">
            <span className="contact-icon" aria-hidden="true">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
                <circle cx="12" cy="10" r="3" />
              </svg>
            </span>
            <span>{CONTACT.location}</span>
          </div>
          <div className="contact-row contact-row-muted">{CONTACT.city}</div>

          <div className="contact-row">
            <span className="contact-icon" aria-hidden="true">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="5" width="18" height="14" rx="2" />
                <path d="M3 7l9 6 9-6" />
              </svg>
            </span>
            <a href={`mailto:${CONTACT.email}`}>{CONTACT.email}</a>
          </div>

          <div className="contact-row">
            <span className="contact-icon" aria-hidden="true">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="6" y="2" width="12" height="20" rx="3" />
                <line x1="12" y1="18" x2="12" y2="18" />
              </svg>
            </span>
            <a href={`tel:${CONTACT.phone.replace(/\s+/g, '')}`}>{CONTACT.phone}</a>
          </div>
        </div>

        <span className="conn-pill">
          <span className={`conn-dot ${isLive ? 'live' : 'demo'}`} />
          {isLive ? 'API Connected' : 'Demo Data'}
        </span>
      </div>
    </aside>
  )
}
