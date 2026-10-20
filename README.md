# AgentOps AI

AI agent testing, observability, and reliability platform for Kritical Hacks 2026.

Loop: **Test → Detect → Investigate → Improve → Retest**.

TinyFish is a first-class adapter: Agent SSE execution, Fetch/Search grounding, and preloaded web-agent cases.

## Run locally

```bash
# backend
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
# optional: copy .env.example to .env and set TINYFISH_API_KEY
uvicorn app.main:app --reload --port 8000
```

```bash
# frontend
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. First API boot creates `backend/agentops.db` and seeds suites, TinyFish cases, and baseline vs candidate runs.

Without `TINYFISH_API_KEY`, the adapter still emits TinyFish `STARTED` / `PROGRESS` / `COMPLETE` and Fetch/Search payloads so the evaluator and UI stay live. With a key, it calls:

- `POST https://agent.tinyfish.ai/v1/automation/run-sse`
- `POST https://api.fetch.tinyfish.ai`
- `GET https://api.search.tinyfish.ai`
