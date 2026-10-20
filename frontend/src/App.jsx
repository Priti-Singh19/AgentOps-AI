import { useCallback, useEffect, useState } from "react";
import { Navigate, Route, Routes, useNavigate } from "react-router-dom";
import Navbar from "./components/Navbar";
import Sidebar from "./components/Sidebar";
import RunSuiteModal from "./components/RunSuiteModal";
import Dashboard from "./pages/Dashboard";
import TestSuites from "./pages/TestSuites";
import Traces from "./pages/Traces";
import Comparison from "./pages/Comparison";
import { api } from "./api";

export default function App() {
  const navigate = useNavigate();
  const [dark, setDark] = useState(true);
  const [overview, setOverview] = useState(null);
  const [suites, setSuites] = useState([]);
  const [versions, setVersions] = useState([]);
  const [runs, setRuns] = useState([]);
  const [modal, setModal] = useState(false);
  const [error, setError] = useState("");
  const [activeRunId, setActiveRunId] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const [ov, su, ve, ru] = await Promise.all([
        api.overview(),
        api.suites(),
        api.versions(),
        api.runs(),
      ]);
      setOverview(ov);
      setSuites(su);
      setVersions(ve);
      setRuns(ru);
      setError("");
    } catch (err) {
      setError(err.message);
    }
  }, []);

  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, 1200);
    return () => clearInterval(timer);
  }, [refresh]);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    document.body.classList.toggle("bg-slate-950", dark);
    document.body.classList.toggle("text-slate-100", dark);
    document.body.classList.toggle("bg-slate-100", !dark);
    document.body.classList.toggle("text-slate-900", !dark);
  }, [dark]);

  function handleStarted(run) {
    setActiveRunId(run.id);
    navigate(`/traces/${run.id}`);
  }

  return (
    <div className={`min-h-screen ${dark ? "bg-slate-950 text-slate-100" : "bg-slate-100 text-slate-900"}`}>
      <div className="flex min-h-screen">
        <Sidebar />
        <div className="flex min-w-0 flex-1 flex-col">
          <Navbar dark={dark} onToggle={() => setDark((value) => !value)} />
          <main className="flex-1 overflow-auto p-6">
            {error ? (
              <div className="mb-4 rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-300">
                Backend unreachable. Start FastAPI on :8000. {error}
              </div>
            ) : null}
            <Routes>
              <Route
                path="/"
                element={
                  <Dashboard
                    overview={overview}
                    onOpenRun={(id) => navigate(`/traces/${id}`)}
                    onRunSuite={() => setModal(true)}
                  />
                }
              />
              <Route
                path="/suites"
                element={<TestSuites suites={suites} versions={versions} onRun={() => setModal(true)} />}
              />
              <Route path="/traces" element={<Traces runs={runs} activeRunId={activeRunId} />} />
              <Route path="/traces/:runId" element={<Traces runs={runs} activeRunId={activeRunId} />} />
              <Route path="/compare" element={<Comparison runs={runs} />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>
        </div>
      </div>
      <RunSuiteModal
        open={modal}
        onClose={() => setModal(false)}
        suites={suites}
        versions={versions}
        onStarted={handleStarted}
      />
    </div>
  );
}
