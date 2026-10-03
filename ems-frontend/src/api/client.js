const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const TOKEN_KEY = 'ems_token'

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
  } catch {
    throw new ApiError('Could not reach the server. Check your connection and try again.', 0)
  }

  // Only treat a 401 as "your session died" for requests that were actually
  // sending a token (auth: true). The login endpoint itself legitimately
  // returns 401 for a wrong password — that's a normal login failure, not an
  // expired session, and must not clear the token or redirect away from the
  // login page the user is already on.
  if (res.status === 401 && auth) {
    clearToken()
    window.location.href = '/login'
    throw new ApiError('Session expired, please log in again', 401)
  }

  let data = null
  const text = await res.text()
  if (text) {
    try { data = JSON.parse(text) } catch { data = null }
  }

  if (!res.ok) {
    const message = data?.message || data?.detail || data?.error?.message || 'Something went wrong'
    throw new ApiError(typeof message === 'string' ? message : JSON.stringify(message), res.status)
  }

  return data
}

export const api = {
  get: (path, params) => request(path, { method: 'GET', params }),
  post: (path, body) => request(path, { method: 'POST', body }),
  put: (path, body) => request(path, { method: 'PUT', body }),
  patch: (path, body) => request(path, { method: 'PATCH', body }),
<<<<<<< HEAD
  del: (path) => request(path, { method: 'DELETE' }),
=======
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6
  login: (body) => request('/api/auth/login', { method: 'POST', body, auth: false }),
}

export { ApiError }