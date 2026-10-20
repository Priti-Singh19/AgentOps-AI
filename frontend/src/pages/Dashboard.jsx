import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Play } from "lucide-react";
import MetricsCards from "../components/MetricsCards";

export default function Dashboard({ overview, onOpenRun, onRunSuite }) {
  const chart = useMemo(
    () =>
      (overview?.version_stats || []).map((row) => ({
        name: row.name,
        "Pass %": Math.round((row.pass_rate || 0) * 100),
        "Latency": Math.round(row.latency_ms || 0),
        "Tools": Math.round(row.tool_call_count || 0),
      })),
    [overview]
  );
  const taxonomy = Object.entries(overview?.taxonomy_counts || {});

  if (!overview) {
    return <p className="text-slate-500">Loading live metrics from SQLite…</p>;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">{overview.project.name}</h1>
          <p className="text-sm text-slate-400">
            Metrics are computed from persisted runs, TinyFish traces, and evaluation rows.
          </p>
        </div>
        <button
          type="button"
          onClick={onRunSuite}
          className="inline-flex items-center gap-2 rounded-lg bg-cyan-500 px-4 py-2 text-sm font-medium text-slate-950 hover:bg-cyan-400"
        >
          <Play size={16} />
          Run test suite
        </button>
      </div>
      <MetricsCards overview={overview} />
      <div className="grid gap-4 xl:grid-cols-[1.4fr_0.8fr]">
        <div className="panel p-4">
          <p className="mb-3 text-sm text-slate-300">Baseline vs candidate regression</p>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chart}>
                <CartesianGrid stroke="#1e293b" />
                <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 12 }} />
                <YAxis tick={{ fill: "#94a3b8", fontSize: 12 }} />
                <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b" }} />
                <Legend />
                <Bar dataKey="Pass %" fill="#34d399" radius={4} />
                <Bar dataKey="Latency" fill="#f59e0b" radius={4} />
                <Bar dataKey="Tools" fill="#22d3ee" radius={4} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="panel p-4">
          <p className="mb-3 text-sm text-slate-300">Failure taxonomy</p>
          <ul className="space-y-2">
            {taxonomy.length === 0 ? (
              <li className="text-sm text-slate-500">No failing assertions yet.</li>
            ) : (
              taxonomy.map(([name, count]) => (
                <li
                  key={name}
                  className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm"
                >
                  <span className="text-slate-300">{name}</span>
                  <span className="text-rose-300">{count}</span>
                </li>
              ))
            )}
          </ul>
        </div>
      </div>
      <div className="panel overflow-hidden">
        <div className="border-b border-slate-800 px-4 py-3 text-sm font-medium">Latest runs</div>
        <table className="w-full text-left text-sm">
          <thead className="text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-2">ID</th>
              <th className="px-4 py-2">Version</th>
              <th className="px-4 py-2">Suite</th>
              <th className="px-4 py-2">Pass</th>
              <th className="px-4 py-2">Latency</th>
              <th className="px-4 py-2">Status</th>
            </tr>
          </thead>
          <tbody>
            {(overview.latest_runs || []).map((run) => (
              <tr
                key={run.id}
                className="cursor-pointer border-t border-slate-800 hover:bg-slate-800/40"
                onClick={() => onOpenRun(run.id)}
              >
                <td className="px-4 py-2 font-mono text-cyan-300">#{run.id}</td>
                <td className="px-4 py-2">{run.version_name}</td>
                <td className="px-4 py-2">{run.suite_name}</td>
                <td className="px-4 py-2 text-emerald-400">{Math.round(run.pass_rate * 100)}%</td>
                <td className="px-4 py-2">{Math.round(run.latency_ms)} ms</td>
                <td className="px-4 py-2">
                  <StatusBadge status={run.status} progress={run.progress} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function StatusBadge({ status, progress }) {
  const map = {
    completed: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
    running: "border-amber-500/30 bg-amber-500/10 text-amber-300",
    queued: "border-slate-600 bg-slate-800 text-slate-300",
    failed: "border-rose-500/30 bg-rose-500/10 text-rose-300",
  };
  return (
    <span className={`chip ${map[status] || map.queued}`}>
      {status}
      {status === "running" ? ` ${progress}%` : ""}
    </span>
  );
}
