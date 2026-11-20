const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";
const SESSION_KEY = "banking_fraud_session";

export function getSession() {
  try {
    return JSON.parse(localStorage.getItem(SESSION_KEY) || "null");
  } catch {
    return null;
  }
}

export function clearSession() {
  localStorage.removeItem(SESSION_KEY);
}

async function request(path, options = {}) {
  const session = getSession();
  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");
  if (session?.access_token) {
    headers.set("Authorization", `Bearer ${session.access_token}`);
  }

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401) clearSession();
    throw new Error(body.detail || `Request failed with status ${response.status}`);
  }
  return body;
}

export async function login(username, password) {
  const token = await request("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  localStorage.setItem(SESSION_KEY, JSON.stringify(token));
  const user = await request("/auth/me");
  const session = { ...token, user };
  localStorage.setItem(SESSION_KEY, JSON.stringify(session));
  return session;
}

export const api = {
  getAccounts: () => request("/accounts"),
  getCustomers: () => request("/customers"),
  getTransactions: () => request("/transactions"),
  createTransfer: (payload) => request("/transactions/transfers", {
    method: "POST",
    body: JSON.stringify(payload),
  }),
  getAlerts: () => request("/fraud/alerts"),
  updateAlertStatus: (alertId, alert_status) => request(`/fraud/alerts/${alertId}/status`, {
    method: "PATCH",
    body: JSON.stringify({ alert_status }),
  }),
  openInvestigation: (alertId, payload = {}) => request(`/fraud/alerts/${alertId}/investigations`, {
    method: "POST",
    body: JSON.stringify(payload),
  }),
  getInvestigations: () => request("/fraud/investigations"),
  getInvestigation: (id) => request(`/fraud/investigations/${id}`),
  assignInvestigation: (id, payload) => request(`/fraud/investigations/${id}/assignment`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  }),
  addInvestigationAction: (id, payload) => request(`/fraud/investigations/${id}/actions`, {
    method: "POST",
    body: JSON.stringify(payload),
  }),
  closeInvestigation: (id, payload) => request(`/fraud/investigations/${id}/close`, {
    method: "POST",
    body: JSON.stringify(payload),
  }),
};
