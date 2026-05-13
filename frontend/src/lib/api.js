// Centralized REST client.

const ACCESS_TOKEN_KEY = 'ta.access_token'
const REFRESH_TOKEN_KEY = 'ta.refresh_token'
const CHILD_TOKEN_KEY = 'ta.child_token'
const ACTIVE_CHILD_KEY = 'ta.active_child_id'

export const auth = {
  setTokens({ access, refresh }) {
    if (access) localStorage.setItem(ACCESS_TOKEN_KEY, access)
    if (refresh) localStorage.setItem(REFRESH_TOKEN_KEY, refresh)
  },
  setChildToken(token) {
    if (token) localStorage.setItem(CHILD_TOKEN_KEY, token)
    else localStorage.removeItem(CHILD_TOKEN_KEY)
  },
  setActiveChild(id) {
    if (id) localStorage.setItem(ACTIVE_CHILD_KEY, id)
    else localStorage.removeItem(ACTIVE_CHILD_KEY)
  },
  getAccess() { return localStorage.getItem(ACCESS_TOKEN_KEY) },
  getRefresh() { return localStorage.getItem(REFRESH_TOKEN_KEY) },
  getChildToken() { return localStorage.getItem(CHILD_TOKEN_KEY) },
  getActiveChildId() { return localStorage.getItem(ACTIVE_CHILD_KEY) },
  clear() {
    localStorage.removeItem(ACCESS_TOKEN_KEY)
    localStorage.removeItem(REFRESH_TOKEN_KEY)
    localStorage.removeItem(CHILD_TOKEN_KEY)
    localStorage.removeItem(ACTIVE_CHILD_KEY)
  },
}

async function refreshAccess() {
  const refresh = auth.getRefresh()
  if (!refresh) return false
  const r = await fetch('/api/auth/refresh', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refresh }),
  })
  if (!r.ok) {
    auth.clear()
    return false
  }
  const j = await r.json()
  auth.setTokens({ access: j.access_token })
  return true
}

export async function api(path, opts = {}) {
  const headers = new Headers(opts.headers || {})
  if (!(opts.body instanceof FormData) && !headers.has('Content-Type') && opts.body) {
    headers.set('Content-Type', 'application/json')
  }
  const token = auth.getAccess()
  if (token) headers.set('Authorization', `Bearer ${token}`)

  let r = await fetch(path, { ...opts, headers })
  if (r.status === 401 && (await refreshAccess())) {
    headers.set('Authorization', `Bearer ${auth.getAccess()}`)
    r = await fetch(path, { ...opts, headers })
  }
  if (!r.ok) {
    let msg
    try { msg = (await r.json()).detail || r.statusText } catch { msg = r.statusText }
    throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg))
  }
  if (r.status === 204) return null
  const ct = r.headers.get('Content-Type') || ''
  return ct.includes('application/json') ? r.json() : r.text()
}

export const authApi = {
  register: ({ email, password, full_name }) =>
    api('/api/auth/register', { method: 'POST', body: JSON.stringify({ email, password, full_name }) }),
  login: async ({ email, password }) => {
    const form = new URLSearchParams()
    form.set('username', email)
    form.set('password', password)
    const r = await fetch('/api/auth/login', { method: 'POST', body: form })
    if (!r.ok) throw new Error('login failed')
    const j = await r.json()
    auth.setTokens({ access: j.access_token, refresh: j.refresh_token })
    return j
  },
  me: () => api('/api/auth/me'),
  logout: () => auth.clear(),
  listChildren: () => api('/api/auth/children'),
  createChild: (payload) =>
    api('/api/auth/children', { method: 'POST', body: JSON.stringify(payload) }),
  issueChildToken: (childId) =>
    api(`/api/auth/children/${childId}/token`, { method: 'POST' }),
}

export const adminApi = {
  list: (name) => api(`/api/admin/${name}`),
  create: (name, payload) => api(`/api/admin/${name}`, { method: 'POST', body: JSON.stringify(payload) }),
  update: (name, id, payload) => api(`/api/admin/${name}/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  remove: (name, id) => api(`/api/admin/${name}/${id}`, { method: 'DELETE' }),
}

export const parentApi = {
  children: () => api('/api/parent/children'),
  mastery: (childId) => api(`/api/parent/children/${childId}/mastery`),
  stumbles: (childId) => api(`/api/parent/children/${childId}/stumbles`),
  sessions: (childId) => api(`/api/parent/children/${childId}/sessions`),
}
