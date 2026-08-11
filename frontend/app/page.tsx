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
          className="flex items-center justify-between mb-7"
          style={{
            background: "var(--color-applied)",
            border: "4px solid var(--color-applied-d)",
            boxShadow: "4px 4px 0 var(--color-applied-d)",
            padding: "14px 20px",
          }}
        >
          <div className="flex items-center gap-3">
            <svg
              viewBox="0 0 24 24"
              width="26"
              height="26"
              fill="none"
              stroke="#fff"
              strokeWidth="1.75"
              strokeLinejoin="miter"
              strokeLinecap="square"
            >
              <path d="M4 4H20V20H4V8H16V16H8V12H12" />
            </svg>
            <h1 className="font-pixel font-bold text-2xl" style={{ color: "#fff" }}>
              offer loop
            </h1>
          </div>
          <div className="flex flex-col items-end gap-1">
            <span className="font-pixel text-xs" style={{ color: "#fff" }}>
              search, apply, repeat.
            </span>
            <span className="font-pixel text-xs" style={{ color: "#D8E4C8" }}>
              {(() => {
                const d = new Date();
                const mm = String(d.getMonth() + 1).padStart(2, "0");
                const dd = String(d.getDate()).padStart(2, "0");
                return `${mm}.${dd}.${d.getFullYear()}`;
              })()}
            </span>
          </div>
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