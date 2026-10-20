import { NavLink } from "react-router-dom";
import { GitCompare, LayoutDashboard, Radio, FlaskConical } from "lucide-react";

const links = [
  { to: "/", label: "Overview", icon: LayoutDashboard },
  { to: "/suites", label: "Test Suites", icon: FlaskConical },
  { to: "/traces", label: "Traces", icon: Radio },
  { to: "/compare", label: "Version Compare", icon: GitCompare },
];

export default function Sidebar() {
  return (
    <aside className="flex w-56 flex-col border-r border-slate-800 bg-slate-950 px-3 py-5">
      <p className="mb-4 px-2 text-[11px] uppercase tracking-[0.2em] text-slate-500">Workspace</p>
      <nav className="space-y-1">
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.to === "/"}
            className={({ isActive }) =>
              `flex items-center gap-2 rounded-lg px-3 py-2 text-sm ${
                isActive
                  ? "bg-slate-900 text-cyan-300"
                  : "text-slate-400 hover:bg-slate-900/70 hover:text-slate-100"
              }`
            }
          >
            <link.icon size={16} />
            {link.label}
          </NavLink>
        ))}
      </nav>
      <div className="mt-auto rounded-lg border border-slate-800 bg-slate-900 p-3 text-xs text-slate-400">
        TinyFish Agent SSE + Fetch grounding is required for web-agent cases.
      </div>
    </aside>
  );
}
