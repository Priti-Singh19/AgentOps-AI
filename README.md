# AgentOps AI 🚀

> **AI Agent Testing, Observability & Reliability Platform**  
> *Stress-test agents, explain every failure with trace evidence, and prove that a prompt/config fix actually works.*

---

## 🏆 Kritical Hacks 2026 Submission

- **Team Name:** PairDev AI
- **Track:** AI/ML Track (Open Innovation)
- **Mandatory Feature:** Full TinyFish Integration (Agent API SSE + Fetch Grounding)

---

## 📌 Problem Statement

A successful demo does not guarantee robust behavior on real-world inputs. AI agents fail in ways that are difficult to reproduce or diagnose:
- Unsupported answers & hallucinations
- Infinite tool loops & repeated actions
- Blown latency and cost budgets
- Unseen regressions when prompt templates change

Standard accuracy metrics tell you *if* an agent failed, but not *how* or *why*. Manual testing misses edge cases, and prompt changes often repair one scenario while breaking three others.

---

## 💡 Solution & Core Workflow

**AgentOps AI** provides a small, repeatable evaluation loop:
Loop: **Test → Detect → Investigate → Improve → Retest**.

1. **Test:** Execute normal, edge-case, and adversarial scenarios with reproducible inputs.
2. **Detect:** Record structured trace events (LLM calls, tool calls, and web events).
3. **Investigate:** Rank root causes using our rule-based evaluation engine and failure taxonomy.
4. **Improve:** Compare a candidate prompt/config against a baseline on identical test suites.
5. **Retest:** Rerun suites to verify pass-rate gains, latency reductions, and tool efficiency.

---

## 🐟 TinyFish Integration (Mandatory Track Requirement)

AgentOps AI natively leverages **TinyFish** to give our observability engine a live window into web-agent execution and real-time grounding:

* **TinyFish Agent SSE Streaming:** Pushes live `STARTED`, `STREAMING_URL`, `PROGRESS`, and `COMPLETE` events directly into AgentOps structured trace timelines.
* **TinyFish Fetch & Search API Grounding:** Fetches live web pages/policy documents and converts them into structured Markdown/JSON reference data to ground and judge agent claims.
* **Web Loop & Anomaly Detection:** Identifies when web-navigation agents get stuck in infinite retry/click loops.

---

## 🛠 Tech Stack

- **Frontend:** React + Vite, Tailwind CSS (Slate Dark Theme), Recharts, Lucide Icons
- **Backend:** Python FastAPI, Pydantic v2, Uvicorn
- **Database:** SQLite (`agentops.db`) via SQLAlchemy ORM
- **Web Agent / Grounding:** TinyFish API (Agent SSE + Fetch)
- **Deployment & Dev:** Cursor AI, Docker Compose ready

---

## 🚦 Failure Taxonomy

AgentOps AI automatically categorizes trace failures into actionable categories:
- **Incorrect Answer:** Fails expected assertions or reference checks.
- **Unsupported Claim:** Claims lack support from TinyFish live web grounding.
- **Tool Misuse:** Unexpected tool call or forbidden tool invoked.
- **Repeated Execution:** Tool retries exceed configured limits.
- **Policy/Safety Failure:** Exposes PII or violates guardrails.
- **Regression:** Candidate version fails previously passing cases.

---

## 💻 How to Run Locally

### Prerequisites
- Python 3.10+
- Node.js 18+

### 1. Backend Setup (FastAPI)
```bash
# Navigate to backend directory (if separated) or root
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run database seed (populates test suites & initial runs)
python app/seed.py

# Start FastAPI backend
uvicorn app.main:app --reload
