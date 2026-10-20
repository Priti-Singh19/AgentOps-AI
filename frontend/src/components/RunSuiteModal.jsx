import { useEffect, useState } from "react";
import { Play, X } from "lucide-react";
import { api } from "../api";

export default function RunSuiteModal({ open, onClose, suites, versions, onStarted }) {
  const [suiteId, setSuiteId] = useState(suites[0]?.id || "");
  const [versionId, setVersionId] = useState(versions[0]?.id || "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setSuiteId(suites[0]?.id || "");
    setVersionId(versions[0]?.id || "");
  }, [suites, versions]);

  if (!open) return null;

  async function launch() {
    setBusy(true);
    setError("");
    try {
      const run = await api.startRun({
        suite_id: Number(suiteId),
        version_id: Number(versionId),
      });
      onStarted(run);
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 p-4">
      <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900 p-5 shadow-2xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Run test suite</h2>
          <button type="button" onClick={onClose} className="text-slate-400 hover:text-white">
            <X size={18} />
          </button>
        </div>
        <label className="mb-3 block text-sm text-slate-400">
          Suite
          <select
            className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-slate-100"
            value={suiteId}
            onChange={(e) => setSuiteId(e.target.value)}
          >
            {suites.map((suite) => (
              <option key={suite.id} value={suite.id}>
                {suite.name}
              </option>
            ))}
          </select>
        </label>
        <label className="mb-4 block text-sm text-slate-400">
          Agent version
          <select
            className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-slate-100"
            value={versionId}
            onChange={(e) => setVersionId(e.target.value)}
          >
            {versions.map((version) => (
              <option key={version.id} value={version.id}>
                {version.name} · {version.model_label}
              </option>
            ))}
          </select>
        </label>
        {error ? <p className="mb-3 text-sm text-rose-400">{error}</p> : null}
        <button
          type="button"
          disabled={busy}
          onClick={launch}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-cyan-500 px-4 py-2 font-medium text-slate-950 hover:bg-cyan-400 disabled:opacity-60"
        >
          <Play size={16} />
          {busy ? "Starting evaluator…" : "Run live against FastAPI"}
        </button>
      </div>
    </div>
  );
}
