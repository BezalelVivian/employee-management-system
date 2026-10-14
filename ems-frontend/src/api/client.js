// In development fall back to the local backend. In a production build there is NO fallback: a missing
// VITE_API_BASE_URL used to make the deployed site silently call http://localhost:8000 (which never works
// for anyone except the developer) and show a baffling "could not reach the server". Now it says what is wrong.
// A trailing slash is removed so "https://api.example.com/" doesn't produce "//api/..." (a 404).
const BASE_URL = (import.meta.env.VITE_API_BASE_URL || (import.meta.env.DEV ? 'http://localhost:8000' : '')).trim().replace(/\/+$/, '')

const TOKEN_KEY = 'ems_token'

// Shown to employees instead of raw Google/server text. The real detail goes to the console only.
const MSG_BUSY = 'The system is busy right now. Please try again in a moment.'
const MSG_TOO_MANY = 'Too many attempts. Please wait a minute and try again.'
const MSG_OFFLINE = 'Could not reach the server. Check your connection and try again.'

// A wrong "current password" is a normal form error, never a dead session, even if some
// server version still answers it with a 401.
const NEVER_LOGOUT_PATHS = ['/api/employee/password', '/api/employee/change-password']

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}
export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}
export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.status = status
  }
}

async function request(path, { method = 'GET', body, params, auth = true } = {}) {
  if (!BASE_URL) {
    throw new ApiError('The app is not connected to its server yet: VITE_API_BASE_URL is not set. Add it in Vercel (Settings -> Environment Variables) and redeploy.', 0)
  }
  let url = `${BASE_URL}${path}`
  if (params) {
    const cleaned = Object.fromEntries(
      Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== '')
    )
    const qs = new URLSearchParams(cleaned).toString()
    if (qs) url += `?${qs}`
  }

  const headers = { 'Content-Type': 'application/json' }
  if (auth) {
    const token = getToken()
    if (token) headers['Authorization'] = `Bearer ${token}`
  }

  let res
  try {
    res = await fetch(url, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  } catch (err) {
    console.error(`[api] ${method} ${path} -> network error`, err)
    throw new ApiError(MSG_OFFLINE, 0)
  }

  // Only treat a 401 as "your session died" for requests that were actually
  // sending a token (auth: true). The login endpoint itself legitimately
  // returns 401 for a wrong password — that's a normal login failure, not an
  // expired session, and must not clear the token or redirect away from the
  // login page the user is already on.
  if (res.status === 401 && auth && !NEVER_LOGOUT_PATHS.some((p) => path.startsWith(p))) {
    clearToken()
    localStorage.removeItem('ems_user')
    if (window.location.pathname !== '/login') window.location.href = '/login'
    throw new ApiError('Session expired, please log in again', 401)
  }

  let data = null
  const text = await res.text()
  if (text) {
    try { data = JSON.parse(text) } catch { data = null }
  }

  if (!res.ok) {
    const raw = data?.message || data?.detail || data?.error?.message || data?.error || text || ''
    const rawText = typeof raw === 'string' ? raw : JSON.stringify(raw)
    if (res.status === 429) {
      console.error(`[api] ${method} ${path} -> 429`, rawText)
      throw new ApiError(MSG_TOO_MANY, 429)
    }
    if (res.status >= 500) {
      // 503s often carry raw Google Sheets text; 500s may carry anything. Keep it out of the UI.
      console.error(`[api] ${method} ${path} -> ${res.status}`, rawText)
      throw new ApiError(MSG_BUSY, res.status)
    }
    // 4xx messages are written for the user, so keep them.
    throw new ApiError(rawText || 'Something went wrong', res.status)
  }

  return data
}

export const api = {
  get: (path, params) => request(path, { method: 'GET', params }),
  post: (path, body) => request(path, { method: 'POST', body }),
  put: (path, body) => request(path, { method: 'PUT', body }),
  patch: (path, body) => request(path, { method: 'PATCH', body }),
  del: (path) => request(path, { method: 'DELETE' }),
  login: (body) => request('/api/auth/login', { method: 'POST', body, auth: false }),
}

export { ApiError }