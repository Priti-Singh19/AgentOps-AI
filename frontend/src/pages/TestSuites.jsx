import { useState } from "react";
import { Play, Plus } from "lucide-react";
import { api } from "../api";

export default function TestSuites({ suites, versions, onRun }) {
  const [suiteId, setSuiteId] = useState(suites[0]?.id);
  const [name, setName] = useState("");
  const [inputText, setInputText] = useState("");
  const [tags, setTags] = useState("tinyfish,web");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  const selected = suites.find((suite) => suite.id === suiteId) || suites[0];

  async function addCase(event) {
    event.preventDefault();
    if (!selected) return;
    setSaving(true);
    setMessage("");
    try {
      await api.createCase(selected.id, {
        name,
        input_text: inputText,
        tags: tags.split(",").map((tag) => tag.trim()).filter(Boolean),
        expected_behaviour: {
          agent_url: "https://example.com",
          agent_goal: inputText,
          ground_with_fetch: tags.includes("tinyfish"),
          expected_tools: tags.includes("tinyfish") ? ["tinyfish.navigate"] : ["lookup_order"],
          required_keys: ["ok"],
        },
      });
      setName("");
      setInputText("");
      setMessage("Test case saved to SQLite.");
      window.location.reload();
    } catch (err) {
      setMessage(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Test suites & cases</h1>
          <p className="text-sm text-slate-400">
            Customer-support refunds plus TinyFish web-agent extraction, grounding, and loops.
          </p>
        </div>
        <button
          type="button"
          onClick={onRun}
          className="inline-flex items-center gap-2 rounded-lg bg-cyan-500 px-4 py-2 text-sm font-medium text-slate-950 hover:bg-cyan-400"
        >
          <Play size={16} />
          Run test suite
        </button>
      </div>
      <div className="flex flex-wrap gap-2">
        {suites.map((suite) => (
          <button
            key={suite.id}
            type="button"
            onClick={() => setSuiteId(suite.id)}
            className={`rounded-lg border px-3 py-2 text-sm ${
              selected?.id === suite.id
                ? "border-cyan-500/40 bg-cyan-500/10 text-cyan-200"
                : "border-slate-800 bg-slate-900 text-slate-400"
            }`}
          >
            {suite.name}
            <span className="ml-2 text-xs text-slate-500">{suite.cases.length} cases</span>
          </button>
        ))}
      </div>
      {selected ? (
        <div className="grid gap-4 xl:grid-cols-[1.3fr_0.7fr]">
          <div className="space-y-3">
            {selected.cases.map((testCase) => (
              <article key={testCase.id} className="panel p-4">
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <h3 className="font-medium text-slate-100">{testCase.name}</h3>
                  {(testCase.tags || []).map((tag) => (
                    <span
                      key={tag}
                      className={`chip ${
                        String(tag).includes("tinyfish")
                          ? "border-cyan-500/30 bg-cyan-500/10 text-cyan-300"
                          : "border-slate-700 text-slate-400"
                      }`}
                    >
                      {tag}
                    </span>
                  ))}
                </div>
                <p className="text-sm text-slate-300">{testCase.input_text}</p>
                <pre className="mt-3 overflow-auto rounded-lg bg-slate-950 p-3 font-mono text-[11px] text-slate-400">
                  {JSON.stringify(testCase.expected_behaviour, null, 2)}
                </pre>
              </article>
            ))}
          </div>
          <form className="panel h-fit space-y-3 p-4" onSubmit={addCase}>
            <p className="flex items-center gap-2 text-sm font-medium">
              <Plus size={16} /> Add case to {selected.name}
            </p>
            <input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Case name"
              className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm"
            />
            <textarea
              required
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Agent input / TinyFish goal"
              rows={4}
              className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm"
            />
            <input
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm"
            />
            <button
              disabled={saving}
              className="w-full rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200 hover:bg-slate-800"
            >
              {saving ? "Saving…" : "Persist test case"}
            </button>
            {message ? <p className="text-xs text-slate-400">{message}</p> : null}
            <p className="text-xs text-slate-500">
              Versions in this project: {versions.map((v) => v.name).join(", ") || "none"}.
            </p>
          </form>
        </div>
      ) : null}
    </div>
  );
}
