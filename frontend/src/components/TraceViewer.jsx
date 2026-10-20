import { useEffect, useMemo, useState } from "react";
import { Fish, Cpu, Wrench, AlertTriangle } from "lucide-react";

function iconFor(type) {
  if (String(type).startsWith("tinyfish")) return Fish;
  if (String(type).startsWith("tool")) return Wrench;
  if (String(type).includes("llm")) return Cpu;
  return AlertTriangle;
}

function tone(status, type) {
  if (status === "error") return "border-rose-500/40 bg-rose-500/10 text-rose-300";
  if (status === "warn") return "border-amber-500/40 bg-amber-500/10 text-amber-300";
  if (String(type).startsWith("tinyfish")) return "border-cyan-500/40 bg-cyan-500/10 text-cyan-300";
  if (String(type).includes("llm")) return "border-indigo-500/40 bg-indigo-500/10 text-indigo-300";
  return "border-slate-700 bg-slate-800/80 text-slate-300";
}

export default function TraceViewer({ traces = [], evaluations = [] }) {
  const [selected, setSelected] = useState(traces[0] || null);
  useEffect(() => {
    setSelected((current) => {
      if (current && traces.some((event) => event.id === current.id)) {
        return traces.find((event) => event.id === current.id) || current;
      }
      return traces[0] || null;
    });
  }, [traces]);
  const groupedFails = useMemo(
    () => evaluations.filter((item) => !item.passed),
    [evaluations]
  );

  if (!traces.length) {
    return (
      <div className="panel p-8 text-sm text-slate-500">
        No trace events yet. Run a suite to stream TinyFish and tool events into SQLite.
      </div>
    );
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
      <div className="panel overflow-hidden">
        <div className="border-b border-slate-800 px-4 py-3 text-sm font-medium text-slate-200">
          Execution timeline
        </div>
        <ol className="max-h-[620px] space-y-2 overflow-auto p-4">
          {traces.map((event) => {
            const Icon = iconFor(event.event_type);
            const active = selected?.id === event.id;
            return (
              <li key={event.id}>
                <button
                  type="button"
                  onClick={() => setSelected(event)}
                  className={`flex w-full items-start gap-3 rounded-lg border px-3 py-2 text-left ${
                    active ? "border-cyan-500/50 bg-slate-800" : "border-slate-800 bg-slate-900/40"
                  }`}
                >
                  <span className={`mt-0.5 rounded-md border p-1 ${tone(event.status, event.event_type)}`}>
                    <Icon size={14} />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="flex items-center justify-between gap-3">
                      <span className="font-mono text-xs text-slate-200">{event.event_type}</span>
                      <span className="text-[11px] text-slate-500">{Math.round(event.duration_ms)} ms</span>
                    </span>
                    <span className="mt-1 block truncate text-xs text-slate-500">
                      {event.payload?.purpose ||
                        event.payload?.type ||
                        event.payload?.source ||
                        event.status}
                    </span>
                  </span>
                </button>
              </li>
            );
          })}
        </ol>
      </div>
      <div className="space-y-4">
        <div className="panel p-4">
          <p className="mb-2 text-sm font-medium text-slate-200">Inspect payload</p>
          <pre className="max-h-[360px] overflow-auto rounded-lg bg-slate-950 p-3 font-mono text-[11px] leading-5 text-cyan-100">
            {JSON.stringify(selected?.payload || {}, null, 2)}
          </pre>
        </div>
        <div className="panel p-4">
          <p className="mb-2 text-sm font-medium text-slate-200">Root-cause findings</p>
          {groupedFails.length === 0 ? (
            <p className="text-sm text-emerald-400">All assertions passed for this run.</p>
          ) : (
            <ul className="space-y-2">
              {groupedFails.map((item) => (
                <li key={item.id} className="rounded-lg border border-rose-500/20 bg-rose-500/10 p-3">
                  <p className="text-xs font-medium text-rose-300">
                    {item.taxonomy || "Failure"} · {item.assertion_name}
                  </p>
                  <p className="mt-1 text-xs text-slate-300">{item.failure_reason}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
