const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }
  return response.json();
}

export const api = {
  overview: () => request("/api/overview"),
  suites: () => request("/api/suites"),
  versions: () => request("/api/versions"),
  runs: () => request("/api/runs"),
  run: (id) => request(`/api/runs/${id}`),
  startRun: (body) => request("/api/runs", { method: "POST", body: JSON.stringify(body) }),
  comparisons: () => request("/api/comparisons"),
  createComparison: (body) =>
    request("/api/comparisons", { method: "POST", body: JSON.stringify(body) }),
  createCase: (suiteId, body) =>
    request(`/api/suites/${suiteId}/cases`, { method: "POST", body: JSON.stringify(body) }),
};
