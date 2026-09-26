import { createContext, useContext, useState, useCallback } from 'react'
import { api, setToken, clearToken, getToken } from '../api/client'

const AuthContext = createContext(null)

function loadStoredUser() {
  const raw = localStorage.getItem('ems_user')
  if (!raw) return null
  try { return JSON.parse(raw) } catch { return null }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(loadStoredUser)

  const login = useCallback(async (email, password) => {
    const data = await api.login({ email, password })
    setToken(data.access_token)
    const nextUser = { role: data.role, name: data.name }
    localStorage.setItem('ems_user', JSON.stringify(nextUser))
    setUser(nextUser)
    return nextUser
  }, [])

  const logout = useCallback(() => {
    clearToken()
    localStorage.removeItem('ems_user')
    setUser(null)
  }, [])

  const isAuthenticated = Boolean(user && getToken())

  return (
    <AuthContext.Provider value={{ user, login, logout, isAuthenticated }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
