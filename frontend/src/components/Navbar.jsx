import { Moon, Sun, Fish } from "lucide-react";

export default function Navbar({ dark, onToggle }) {
  return (
    <header className="flex h-16 items-center justify-between border-b border-slate-800 bg-slate-950/90 px-6 backdrop-blur">
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-cyan-500/15 text-cyan-300">
          <Fish size={18} />
        </div>
        <div>
          <p className="text-sm font-semibold tracking-tight text-slate-100">AgentOps AI</p>
          <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">
            Test · Detect · Investigate · Improve · Retest
          </p>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <span className="chip border-indigo-500/30 bg-indigo-500/10 text-indigo-300">PairDev AI</span>
        <button
          type="button"
          onClick={onToggle}
          className="rounded-lg border border-slate-800 bg-slate-900 p-2 text-slate-300 hover:text-white"
          aria-label="Toggle theme"
        >
          {dark ? <Sun size={16} /> : <Moon size={16} />}
        </button>
      </div>
    </header>
  );
}
