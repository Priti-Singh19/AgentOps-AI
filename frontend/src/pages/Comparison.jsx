import { useEffect, useMemo, useState } from "react";
import ComparisonView from "../components/ComparisonView";
import { api } from "../api";

export default function Comparison({ runs }) {
  const completed = runs.filter((run) => run.status === "completed");
  const baselineDefault = completed.find((run) => run.version_name === "Baseline")?.id || completed[0]?.id;
  const candidateDefault =
    completed.find((run) => run.version_name === "Candidate" && run.suite_id === completed.find((r) => r.id === baselineDefault)?.suite_id)?.id ||
    completed.find((run) => run.version_name === "Candidate")?.id ||
    completed[1]?.id;
  const [baselineId, setBaselineId] = useState(baselineDefault || "");
  const [candidateId, setCandidateId] = useState(candidateDefault || "");
  const [delta, setDelta] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setBaselineId(baselineDefault || "");
    setCandidateId(candidateDefault || "");
  }, [baselineDefault, candidateDefault]);

  const baseline = completed.find((run) => run.id === Number(baselineId));
  const candidate = completed.find((run) => run.id === Number(candidateId));

  const previewDelta = useMemo(() => {
    if (!baseline || !candidate) return null;
    return {
      pass_rate_delta: candidate.pass_rate - baseline.pass_rate,
      latency_delta_ms: candidate.latency_ms - baseline.latency_ms,
      tool_call_delta: candidate.tool_call_count - baseline.tool_call_count,
      cost_delta_usd: candidate.cost_usd - baseline.cost_usd,
    };
  }, [baseline, candidate]);

  async function persist() {
    setError("");
    try {
      const row = await api.createComparison({
        baseline_run_id: Number(baselineId),
        candidate_run_id: Number(candidateId),
      });
      setDelta(row.delta_metrics);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">Version comparison</h1>
        <p className="text-sm text-slate-400">
          Side-by-side A/B of Baseline vs Candidate prompt/config using real run aggregates.
        </p>
      </div>
      <div className="panel grid gap-3 p-4 md:grid-cols-[1fr_1fr_auto]">
        <select
          className="rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm"
          value={baselineId}
          onChange={(e) => setBaselineId(e.target.value)}
        >
          {completed.map((run) => (
            <option key={run.id} value={run.id}>
              #{run.id} {run.version_name} · {run.suite_name}
            </option>
          ))}
        </select>
        <select
          className="rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm"
          value={candidateId}
          onChange={(e) => setCandidateId(e.target.value)}
        >
          {completed.map((run) => (
            <option key={run.id} value={run.id}>
              #{run.id} {run.version_name} · {run.suite_name}
            </option>
          ))}
        </select>
        <button
          type="button"
          onClick={persist}
          className="rounded-lg bg-indigo-500 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-400"
        >
          Save comparison
        </button>
      </div>
      {error ? <p className="text-sm text-rose-400">{error}</p> : null}
      <ComparisonView baseline={baseline} candidate={candidate} delta={delta || previewDelta} />
    </div>
  );
}
