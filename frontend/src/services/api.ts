import type { AgentResponse, AITableContext, Filters } from "../types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

function query(filters: Filters) {
  const p = new URLSearchParams();
  if (filters.year) p.set("year", String(filters.year));
  if (filters.category) p.set("category", filters.category);
  if (filters.city) p.set("city", filters.city);
  const q = p.toString();
  return q ? `?${q}` : "";
}

export async function getDashboard(path: string, filters: Filters) {
  const response = await fetch(`${API_BASE}/api/dashboard/${path}${query(filters)}`);
  if (!response.ok) throw new Error("Unable to load dashboard data");
  return response.json();
}

export async function askAgent(payload: {
  message: string;
  session_id: string;
  table: AITableContext;
}): Promise<AgentResponse> {
  const response = await fetch(`${API_BASE}/api/agent/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? "AI Assistant is temporarily unavailable");
  }
  return response.json();
}
