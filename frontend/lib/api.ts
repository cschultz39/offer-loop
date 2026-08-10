const isServer = typeof window === "undefined";

function apiUrl(path: string) {
  return isServer ? `${process.env.FASTAPI_URL}${path}` : `/api${path}`;
}

function apiHeaders(): HeadersInit {
  const headers: HeadersInit = { "Content-Type": "application/json" };
  if (isServer) headers["x-api-key"] = process.env.API_SECRET!;
  return headers;
}

export async function getMetrics() {
  const res = await fetch(apiUrl("/metrics"), { headers: apiHeaders(), cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch metrics");
  return res.json();
}

export async function getWeeklyHistory() {
  const res = await fetch(apiUrl("/history"), { headers: apiHeaders(), cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch history");
  return res.json();
}

export async function getUnappliedJobs() {
  const res = await fetch(apiUrl("/jobs?status=not+applied&limit=10"), { headers: apiHeaders(), cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch jobs");
  return res.json();
}

export async function markApplied(jobId: string) {
  const res = await fetch(apiUrl("/jobs/status"), {
    method: "PATCH",
    headers: apiHeaders(),
    body: JSON.stringify({ job_id: jobId, new_status: "applied" }),
  });
  if (!res.ok) throw new Error("Failed to update status");
  return res.json();
}

export async function markNotInterested(jobId: string) {
  const res = await fetch(apiUrl("/jobs/not-interested"), {
    method: "PATCH",
    headers: apiHeaders(),
    body: JSON.stringify({ job_id: jobId }),
  });
  if (!res.ok) throw new Error("Failed to update status");
  return res.json();
}

export async function sendChatMessage(message: string, conversationHistory: any[] = []) {
  const res = await fetch(apiUrl("/chat"), {
    method: "POST",
    headers: apiHeaders(),
    body: JSON.stringify({ message, conversation_history: conversationHistory }),
  });
  if (!res.ok) throw new Error("Failed to reach chat agent");
  return res.json();
}