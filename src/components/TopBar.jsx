import { useClock } from '../hooks/useApi'

export default function TopBar({ title, isLive }) {
  const now = useClock()

  const time = now.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })
  const date = now.toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' })

  return (
    <header className="topbar">
      <div className="topbar-title">
        {title}
        <span className="topbar-crumb">/ SRMIST Fab Lab</span>
      </div>
      {isLive === false && (
        <span className="demo-banner" role="status">
          Demo mode — sample data, no backend attached
        </span>
      )}
      <div className="topbar-clock mono">
        {time}
        <span className="topbar-date">{date}</span>
      </div>
    </header>
  )
}
