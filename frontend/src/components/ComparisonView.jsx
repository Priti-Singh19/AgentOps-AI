import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const axis = { fill: "#94a3b8", fontSize: 12 };
const grid = { stroke: "#1e293b" };

export default function ComparisonView({ baseline, candidate, delta }) {
  const bars = [
    {
      metric: "Pass rate %",
      Baseline: Math.round((baseline?.pass_rate || 0) * 100),
      Candidate: Math.round((candidate?.pass_rate || 0) * 100),
    },
    {
      metric: "Latency ms",
      Baseline: Math.round(baseline?.latency_ms || 0),
      Candidate: Math.round(candidate?.latency_ms || 0),
    },
    {
      metric: "Tool calls",
      Baseline: baseline?.tool_call_count || 0,
      Candidate: candidate?.tool_call_count || 0,
    },
    {
      metric: "Cost ×1000",
      Baseline: Math.round((baseline?.cost_usd || 0) * 1000),
      Candidate: Math.round((candidate?.cost_usd || 0) * 1000),
    },
  ];
  const line = [
    { step: "Baseline", pass: Math.round((baseline?.pass_rate || 0) * 100) },
    { step: "Candidate", pass: Math.round((candidate?.pass_rate || 0) * 100) },
  ];

  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-4">
        <Delta label="Pass rate Δ" value={delta?.pass_rate_delta} pct />
        <Delta label="Latency Δ" value={delta?.latency_delta_ms} suffix=" ms" invert />
        <Delta label="Tool calls Δ" value={delta?.tool_call_delta} invert />
        <Delta label="Cost Δ" value={delta?.cost_delta_usd} prefix="$" invert />
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <div className="panel p-4">
          <p className="mb-3 text-sm text-slate-300">Baseline vs candidate metrics</p>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={bars}>
                <CartesianGrid {...grid} />
                <XAxis dataKey="metric" tick={axis} />
                <YAxis tick={axis} />
                <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b" }} />
                <Legend />
                <Bar dataKey="Baseline" fill="#64748b" radius={4} />
                <Bar dataKey="Candidate" fill="#22d3ee" radius={4} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="panel p-4">
          <p className="mb-3 text-sm text-slate-300">Regression pass-rate trend</p>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={line}>
                <CartesianGrid {...grid} />
                <XAxis dataKey="step" tick={axis} />
                <YAxis tick={axis} domain={[0, 100]} />
                <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b" }} />
                <Line type="monotone" dataKey="pass" stroke="#34d399" strokeWidth={3} dot />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}

function Delta({ label, value, pct, suffix = "", prefix = "", invert = false }) {
  const num = Number(value || 0);
  const good = invert ? num <= 0 : num >= 0;
  return (
    <div className="panel p-4">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mt-2 text-xl font-semibold ${good ? "text-emerald-400" : "text-rose-400"}`}>
        {num > 0 ? "+" : ""}
        {prefix}
        {pct ? Math.round(num * 100) : Number.isInteger(num) ? num : num.toFixed(3)}
        {pct ? "%" : suffix}
      </p>
    </div>
  );
}
