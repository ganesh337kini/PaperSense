/**
 * script.js
 * Phase 1 responsibilities only:
 *  1. Ping the backend's /api/health endpoint on page load to confirm the
 *     frontend and backend are actually connected.
 *  2. Handle the search form submit (real search logic is added in Phase 6
 *     once academic paper APIs are integrated — for now it just confirms
 *     the round trip to the backend works).
 */

const API_BASE = ""; // same origin, since FastAPI serves this page too

async function checkBackendHealth() {
  const statusEl = document.getElementById("backend-status");
  try {
    const res = await fetch(`${API_BASE}/api/health`);
    if (!res.ok) throw new Error(`Status ${res.status}`);
    const data = await res.json();
    statusEl.textContent = `online (${data.app} v${data.version})`;
    statusEl.className = "ok";
  } catch (err) {
    statusEl.textContent = "unreachable — is uvicorn running?";
    statusEl.className = "down";
  }
}

function handleSearchSubmit(event) {
  event.preventDefault();

  const input = document.getElementById("query-input");
  const statusLine = document.getElementById("status-line");
  const resultsEl = document.getElementById("results");

  const query = input.value.trim();
  if (!query) return;

  // Real search (calling /api/search) is wired up in Phase 6.
  // For now, this proves the form → JS → (future) backend flow works.
  statusLine.textContent = `Received query: "${query}" — search API not implemented yet (Phase 6).`;
  resultsEl.innerHTML = "";
}

document.addEventListener("DOMContentLoaded", () => {
  checkBackendHealth();
  document
    .getElementById("search-form")
    .addEventListener("submit", handleSearchSubmit);
});
