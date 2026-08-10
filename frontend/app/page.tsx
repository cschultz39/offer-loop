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
      <h1
        className="font-pixel font-bold text-3xl mb-7 inline-block"
                style={{
                  background: "var(--color-applied)",
                  color: "#fff",
                  padding: "10px 18px",
                  border: "4px solid var(--color-applied-d)",
                  boxShadow: "4px 4px 0 var(--color-applied-d)",
                }}
      >
        OfferLoop
      </h1>

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