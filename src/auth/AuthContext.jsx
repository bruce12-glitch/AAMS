import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { clearSession, getSession, loginWithBackend } from './srmAuth'

const AuthCtx = createContext(null)

export function AuthProvider({ children }) {
  const [session, setSession] = useState(() => getSession())

  const login = useCallback(async (email, password) => {
    const s = await loginWithBackend(email, password)
    setSession(s)
    return s
  }, [])

  const logout = useCallback(() => {
    clearSession()
    setSession(null)
  }, [])

  useEffect(() => {
    window.addEventListener('aams-session-expired', logout)
    return () => window.removeEventListener('aams-session-expired', logout)
  }, [logout])

  const value = useMemo(
    () => ({
      session,
      userEmail: session?.email ?? null,
      isAuthed: Boolean(session),
      isAdmin: session?.role === 'admin',
      login,
      logout
    }),
    [session, login, logout]
  )
  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthCtx)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
