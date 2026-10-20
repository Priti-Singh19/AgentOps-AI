import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import TraceViewer from "../components/TraceViewer";
import { StatusBadge } from "./Dashboard";
import { api } from "../api";

export default function Traces({ runs, activeRunId }) {
  const { runId } = useParams();
  const navigate = useNavigate();
  const selectedId = Number(runId || activeRunId || runs[0]?.id);
  const [detail, setDetail] = useState(null);

  useEffect(() => {
    if (!selectedId) return undefined;
    let cancelled = false;
    async function load() {
      const data = await api.run(selectedId);
      if (!cancelled) setDetail(data);
    }
    load();
    const timer = setInterval(load, 900);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [selectedId]);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">Execution traces</h1>
        <p className="text-sm text-slate-400">
          Step timeline includes LLM calls, tool calls, and TinyFish STARTED/PROGRESS/COMPLETE events.
        </p>
      </div>
      <div className="flex flex-wrap gap-2">
        {runs.map((run) => (
          <button
            key={run.id}
            type="button"
            onClick={() => navigate(`/traces/${run.id}`)}
            className={`rounded-lg border px-3 py-2 text-left text-sm ${
              selectedId === run.id
                ? "border-cyan-500/40 bg-cyan-500/10"
                : "border-slate-800 bg-slate-900"
            }`}
          >
            <span className="block font-mono text-xs text-cyan-300">Run #{run.id}</span>
            <span className="text-slate-300">
              {run.version_name} · {run.suite_name}
            </span>
          </button>
        ))}
      </div>
      {detail ? (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-3 text-sm text-slate-400">
            <StatusBadge status={detail.status} progress={detail.progress} />
            <span>Pass {Math.round(detail.pass_rate * 100)}%</span>
            <span>{Math.round(detail.latency_ms)} ms</span>
            <span>{detail.tool_call_count} tools</span>
            <span>${Number(detail.cost_usd || 0).toFixed(4)}</span>
          </div>
          {detail.status === "running" ? (
            <div className="h-2 overflow-hidden rounded-full bg-slate-800">
              <div className="h-full bg-cyan-400" style={{ width: `${detail.progress}%` }} />
            </div>
          ) : null}
          <TraceViewer traces={detail.traces} evaluations={detail.evaluations} />
        </div>
      ) : (
        <p className="text-slate-500">Select a run to inspect traces.</p>
      )}
    </div>
  );
}
