const API_URL = "/api";

export async function getMetrics() {
    const res = await fetch(`${API_URL}/metrics`, { cache: "no-store" })
    if (!res.ok) throw new Error("Failed to fetch metrics");
    return res.json();
}

export async function getWeeklyHistory() {
    const res = await fetch(`${API_URL}/history`, { cache: "no-store" })
    if (!res.ok) throw new Error("Failed to fetch history");
    return res.json();
}

export async function getUnappliedJobs() {
    const res = await fetch(`${API_URL}/jobs?status=not+applied&limit=10`, { cache: "no-store" })
    if (!res.ok) throw new Error("Failed to fetch jobs");
    return res.json();
}

export async function markApplied(jobId: string) {
    const res = await fetch(`${API_URL}/jobs/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_id: jobId, new_status: "applied" }),
    })
    if (!res.ok) throw new Error("Failed to update status");
    return res.json();
}

export async function markNotInterested(jobId: string) {
    const res = await fetch(`${API_URL}/jobs/not-interested`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_id: jobId }),
    })
    if (!res.ok) throw new Error("Failed to update status");
    return res.json();
}

export async function sendChatMessage(message: string, conversationHistory: any[] = []) {
    const res = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, conversation_history: conversationHistory }),
    })
    if (!res.ok) throw new Error("Failed to reach chat agent");
    return res.json();
}