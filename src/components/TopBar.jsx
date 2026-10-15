import { LAB_TIME_ZONE } from '../utils/time'
import { useClock } from '../hooks/useApi'
import { useAuth } from '../auth/AuthContext'

export default function TopBar({ title, isLive }) {
  const now = useClock()
  const { userEmail, session, logout } = useAuth()

  const time = now.toLocaleTimeString('en-IN', { timeZone: LAB_TIME_ZONE, hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })
  const date = now.toLocaleDateString('en-IN', { timeZone: LAB_TIME_ZONE, weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' })

  return (
    <header className="topbar">
      <div className="topbar-title">
        {title}
        <span className="topbar-crumb">/ FacePass Fab Lab</span>
      </div>
      {isLive === false && (
        <span className="demo-banner" role="status">
          Backend unavailable — displayed data may be samples
        </span>
      )}
      <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginLeft: 'auto' }}>
        {userEmail && (
          <span className="topbar-user" title={userEmail}>
            <span className="topbar-user-dot" aria-hidden="true" />
            <span className="mono">{userEmail}</span>
            <span className={`badge ${session?.role === 'admin' ? 'active' : 'pending'}`}>
              {session?.role ?? 'member'}
            </span>
            <button className="btn sm ghost" type="button" onClick={logout} title="Sign out">
              Sign out
            </button>
          </span>
        )}
        <div className="topbar-clock mono">
          {time}
          <span className="topbar-date">{date}</span>
        </div>
      </div>
    </header>
  )
}
