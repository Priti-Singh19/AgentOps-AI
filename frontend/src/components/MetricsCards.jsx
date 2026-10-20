import { Activity, Clock3, Coins, Fish, Percent, Wrench } from "lucide-react";

function Card({ icon: Icon, label, value, hint, accent }) {
  return (
    <div className="panel p-4">
      <div className="mb-3 flex items-center justify-between">
        <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
        <Icon size={16} className={accent} />
      </div>
      <p className="text-2xl font-semibold text-slate-100">{value}</p>
      {hint ? <p className="mt-1 text-xs text-slate-500">{hint}</p> : null}
    </div>
  );
}

export default function MetricsCards({ overview }) {
  if (!overview) return null;
  return (
    <div className="grid gap-4 md:grid-cols-3 xl:grid-cols-6">
      <Card
        icon={Percent}
        label="Pass rate"
        value={`${Math.round((overview.pass_rate || 0) * 100)}%`}
        hint={`${overview.completed_runs} completed runs`}
        accent="text-emerald-400"
      />
      <Card
        icon={Activity}
        label="Total runs"
        value={overview.total_runs}
        hint="Queued, running, completed"
        accent="text-cyan-400"
      />
      <Card
        icon={Clock3}
        label="Median latency"
        value={`${Math.round(overview.median_latency_ms)} ms`}
        hint="Per suite run"
        accent="text-amber-400"
      />
      <Card
        icon={Wrench}
        label="Tools / task"
        value={overview.tool_calls_per_task}
        hint="Includes TinyFish navigate/fetch"
        accent="text-indigo-400"
      />
      <Card
        icon={Coins}
        label="Est. cost"
        value={`$${Number(overview.estimated_cost_usd || 0).toFixed(3)}`}
        hint="LLM + TinyFish step model"
        accent="text-rose-400"
      />
      <Card
        icon={Fish}
        label="TinyFish events"
        value={overview.tinyfish_events}
        hint="Persisted SSE / Fetch / Search"
        accent="text-cyan-300"
      />
    </div>
  );
}
