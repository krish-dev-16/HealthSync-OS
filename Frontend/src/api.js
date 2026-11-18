async function handle(res) {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `${res.status} ${res.statusText}`);
  }
  return res.json();
}

const post = (url) => fetch(url, { method: "POST" }).then(handle);

export const api = {
  health: () => fetch("/api/health").then(handle),
  patients: () => fetch("/api/patients").then(handle),
  workflow: (id) => fetch(`/api/workflow/${id}`).then(handle),
  run: (id) => post(`/api/workflow/run/${id}`),
  approve: (id) => post(`/api/workflow/approve/${id}`),
  reset: (id) => post(`/api/workflow/reset/${id}`),
};
