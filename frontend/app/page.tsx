import MetricsTiles from "@/components/MetricsTiles";
import { getMetrics } from "@/lib/api";

import StatusChart from "@/components/StatusChart";
import { getWeeklyHistory } from "@/lib/api";

import UnappliedJobs from "@/components/UnappliedJobs";
import { getUnappliedJobs } from "@/lib/api";

import ChatWidget from "@/components/ChatWidget";

export default async function Home() {
  const metrics = await getMetrics();
  const weeklyHistory = await getWeeklyHistory();
  const unappliedJobs = await getUnappliedJobs();

  return (
    <main className="max-w-295 mx-auto px-10 py-8">
      <div>
        <div
          className="flex items-center justify-between mb-2"
          style={{
            background: "var(--color-applied)",
            border: "4px solid var(--color-applied-d)",
            boxShadow: "4px 4px 0 var(--color-applied-d)",
            padding: "14px 20px",
          }}
        >
          <div className="flex items-center gap-3">
            <svg width="28" height="28" viewBox="0 0 28 28" style={{ imageRendering: "pixelated" }}>
              <rect x="12" y="2" width="5" height="5" fill="#fff" />
              <rect x="17" y="2" width="5" height="5" fill="#fff" />
              <rect x="20" y="8" width="5" height="5" fill="#fff" />
              <rect x="20" y="13" width="5" height="5" fill="#fff" />
              <rect x="15" y="18" width="5" height="5" fill="#fff" />
              <rect x="8" y="16" width="5" height="5" fill="#fff" />
              <rect x="5" y="11" width="5" height="5" fill="#fff" />
              <rect x="8" y="6" width="5" height="5" fill="#fff" />
              <rect x="12" y="11" width="5" height="5" fill="#fff" />
            </svg>
            <h1 className="font-pixel font-bold text-2xl" style={{ color: "#fff" }}>
              offer loop
            </h1>
          </div>
          <span className="font-pixel text-xs" style={{ color: "#fff" }}>
            {new Date().toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
          </span>
        </div>
        <p
          className="font-pixel text-xs mb-7"
          style={{ color: "var(--color-applied-d)" }}
        >
          search, apply, repeat.
        </p>
      </div>
      
      <div>
        <h2
          className="font-pixel font-semibold text-med mb-3 inline-block"
          style={{
            background: "var(--color-not-applied)",
            color: "#fff",
            padding: "6px 12px",
            border: "3px solid var(--color-not-applied-d)",
            boxShadow: "3px 3px 0 var(--color-not-applied-d)",
          }}
        >
          status metrics
        </h2>
      </div>
      
      <MetricsTiles data={metrics} />

      <div className="grid grid-cols-[1.4fr_1fr] gap-4 mt-6">
        <div>
        <h2
          className="font-pixel font-semibold text-med mb-3 inline-block"
          style={{
            background: "var(--color-not-applied)",
            color: "#fff",
            padding: "6px 12px",
            border: "3px solid var(--color-not-applied-d)",
            boxShadow: "3px 3px 0 var(--color-not-applied-d)",
          }}
        >
          status history
        </h2>
          <div className="card">
          <StatusChart data={weeklyHistory} />
          </div>
        </div>

        <div>
        <h2
          className="font-pixel font-semibold text-med mb-3 inline-block"
          style={{
            background: "var(--color-not-applied)",
            color: "#fff",
            padding: "6px 12px",
            border: "3px solid var(--color-not-applied-d)",
            boxShadow: "3px 3px 0 var(--color-not-applied-d)",
          }}
        >
          top unapplied
        </h2>
          <div className="card" style={{ height: 300, overflowY: "auto", padding: "14px 16px" }}>
            <UnappliedJobs initialJobs={unappliedJobs} />
          </div>
        </div>
      </div>
      <ChatWidget />
    </main>
  );
}