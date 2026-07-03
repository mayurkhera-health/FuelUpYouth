// Admin API helper. Bearer token persisted in localStorage (the rest of the app
// keeps session in memory only, but the admin needs to survive refreshes on its
// own /admin route group).
const API = import.meta.env.VITE_API_URL ?? "";
const TOKEN_KEY = "fuelup_admin_token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || "";
}
export function setToken(t) {
  localStorage.setItem(TOKEN_KEY, t);
}
export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

// Thrown on 401 so callers can bounce back to the login screen.
export class AuthError extends Error {}

export async function adminFetch(path, opts = {}) {
  const headers = { ...(opts.headers || {}) };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (opts.body && !headers["Content-Type"]) headers["Content-Type"] = "application/json";

  const res = await fetch(`${API}/api/admin${path}`, { ...opts, headers });
  if (res.status === 401) {
    clearToken();
    throw new AuthError("Session expired");
  }
  let data = null;
  try {
    data = await res.json();
  } catch {
    /* empty body */
  }
  if (!res.ok) {
    const msg = (data && data.detail) || `Request failed (${res.status})`;
    throw new Error(msg);
  }
  return data;
}

export async function adminLogin(password) {
  const res = await fetch(`${API}/api/admin/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  });
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new Error((data && data.detail) || "Login failed");
  setToken(data.token);
  return data;
}
