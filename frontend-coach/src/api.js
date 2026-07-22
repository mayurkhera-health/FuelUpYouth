const BASE = import.meta.env.VITE_API_URL ?? ''

export function getToken() { return localStorage.getItem('tc_token') }
export function setToken(t) { localStorage.setItem('tc_token', t) }
export function clearToken() { localStorage.removeItem('tc_token') }

async function apiFetch(path, opts = {}) {
  const token = getToken()
  const headers = { 'Content-Type': 'application/json', ...opts.headers }
  if (token) headers['Authorization'] = `Bearer ${token}`
  const res = await fetch(`${BASE}${path}`, { ...opts, headers })
  if (res.status === 401) { clearToken(); window.location.reload() }
  return res
}

export async function login(email, password) {
  const res = await apiFetch('/api/team-coach/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
  if (!res.ok) throw new Error('Invalid email or password')
  return res.json()
}

export async function fetchTeams() {
  const res = await apiFetch('/api/team-coach/teams/')
  if (!res.ok) throw new Error('Failed to load teams')
  return res.json()
}

export async function fetchRoster(teamId) {
  const res = await apiFetch(`/api/team-coach/teams/${teamId}/roster`)
  if (!res.ok) throw new Error('Failed to load roster')
  return res.json()
}

export async function fetchEngagement(teamId) {
  const res = await apiFetch(`/api/team-coach/teams/${teamId}/engagement`)
  if (!res.ok) throw new Error('Failed to load engagement data')
  return res.json()
}
