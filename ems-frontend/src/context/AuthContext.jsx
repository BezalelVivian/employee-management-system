import { createContext, useContext, useState, useCallback } from 'react'
import { api, setToken, clearToken, getToken } from '../api/client'

const AuthContext = createContext(null)

<<<<<<< HEAD
const PHOTO_KEY = 'ems_photo'

=======
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6
function loadStoredUser() {
  const raw = localStorage.getItem('ems_user')
  if (!raw) return null
  try { return JSON.parse(raw) } catch { return null }
}

<<<<<<< HEAD
function loadStoredPhoto() {
  try { return localStorage.getItem(PHOTO_KEY) || null } catch { return null }
}

function storePhoto(photo) {
  try {
    if (photo) localStorage.setItem(PHOTO_KEY, photo)
    else localStorage.removeItem(PHOTO_KEY)
  } catch { /* storage full/blocked: the photo just isn't cached */ }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(loadStoredUser)
  // The signed-in employee's own photo (data URL). Cached in localStorage so it shows
  // instantly on reload; refreshed from the server once per page load by Layout.
  const [photo, setPhotoState] = useState(loadStoredPhoto)

  const setPhoto = useCallback((next) => {
    setPhotoState(next || null)
    storePhoto(next || null)
  }, [])
=======
export function AuthProvider({ children }) {
  const [user, setUser] = useState(loadStoredUser)
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6

  const login = useCallback(async (email, password) => {
    const data = await api.login({ email, password })
    setToken(data.access_token)
    const nextUser = { role: data.role, name: data.name }
    localStorage.setItem('ems_user', JSON.stringify(nextUser))
<<<<<<< HEAD
    setPhoto(null) // never show the previous person's cached photo
    setUser(nextUser)
    return nextUser
  }, [setPhoto])
=======
    setUser(nextUser)
    return nextUser
  }, [])
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6

  const logout = useCallback(() => {
    clearToken()
    localStorage.removeItem('ems_user')
<<<<<<< HEAD
    setPhoto(null)
    setUser(null)
  }, [setPhoto])

  // Best-effort: a failure (no Photos tab, network blip) just leaves initials showing.
  const refreshPhoto = useCallback(async () => {
    try {
      const res = await api.get('/api/employee/photo')
      setPhoto(res?.photo || null)
    } catch { /* keep whatever is cached */ }
  }, [setPhoto])
=======
    setUser(null)
  }, [])
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6

  const isAuthenticated = Boolean(user && getToken())

  return (
<<<<<<< HEAD
    <AuthContext.Provider value={{ user, login, logout, isAuthenticated, photo, setPhoto, refreshPhoto }}>
=======
    <AuthContext.Provider value={{ user, login, logout, isAuthenticated }}>
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
