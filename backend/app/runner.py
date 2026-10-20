"""Execute a test suite against an agent version and persist traces."""

from __future__ import annotations

import time
from typing import Any

from sqlalchemy.orm import Session

from app.adapters.tinyfish import TinyFishAdapter
from app.evaluator import evaluate_case, summarize
from app.models import AgentVersion, EvaluationResult, Run, TestCase, TestSuite, TraceEvent

COST_PER_TOOL = 0.002
COST_PER_LLM = 0.0015
COST_PER_TINYFISH = 0.012


def execute_run(db: Session, run_id: int) -> Run:
    run = db.get(Run, run_id)
    if not run:
        raise ValueError(f"Run {run_id} not found")
    version = db.get(AgentVersion, run.version_id)
    suite = db.get(TestSuite, run.suite_id)
    cases = list(suite.cases) if suite else []
    run.status = "running"
    run.progress = 0
    db.commit()

    adapter = TinyFishAdapter()
    step = 0
    tool_calls_total = 0
    latencies: list[float] = []
    all_eval_passed = 0
    eval_total = 0
    cost = 0.0

    for index, case in enumerate(cases):
        started = time.perf_counter()
        execution = _execute_case(adapter, version, case)
        case_latency = (time.perf_counter() - started) * 1000
        latencies.append(case_latency)
        tool_calls_total += len(execution["tool_calls"])
        cost += _estimate_cost(execution)

        persisted_events: list[dict[str, Any]] = []
        for event in execution["events"]:
            step += 1
            row = TraceEvent(
                run_id=run.id,
                test_case_id=case.id,
                step=step,
                event_type=event["event_type"],
                payload=event.get("payload") or {},
                duration_ms=float(event.get("duration_ms") or 0),
                status=event.get("status") or "ok",
            )
            db.add(row)
            persisted_events.append(
                {
                    "event_type": row.event_type,
                    "payload": row.payload,
                    "status": row.status,
                    "duration_ms": row.duration_ms,
                }
            )

        reference_text = ""
        if isinstance(case.reference_data, dict):
            reference_text = str(
                case.reference_data.get("markdown")
                or case.reference_data.get("text")
                or ""
            )
        evals = evaluate_case(
            test_case={
                "expected_behaviour": case.expected_behaviour or {},
                "tags": case.tags or [],
            },
            output=execution["output"],
            tool_calls=execution["tool_calls"],
            events=persisted_events,
            latency_ms=case_latency,
            reference_text=reference_text,
        )
        for item in evals:
            db.add(
                EvaluationResult(
                    run_id=run.id,
                    test_case_id=case.id,
                    assertion_name=item["assertion_name"],
                    passed=item["passed"],
                    score=item["score"],
                    failure_reason=item["failure_reason"],
                    taxonomy=item["taxonomy"],
                )
            )
        summary = summarize(evals)
        eval_total += 1
        if summary["passed"]:
            all_eval_passed += 1

        run.progress = int(((index + 1) / max(len(cases), 1)) * 100)
        run.tool_call_count = tool_calls_total
        run.latency_ms = round(sum(latencies) / max(len(latencies), 1), 2)
        run.cost_usd = round(cost, 4)
        run.pass_rate = round(all_eval_passed / max(eval_total, 1), 4)
        db.commit()

    run.status = "completed"
    run.progress = 100
    db.commit()
    db.refresh(run)
    return run


def fail_run(db: Session, run_id: int, message: str) -> None:
    run = db.get(Run, run_id)
    if not run:
        return
    run.status = "failed"
    run.error_message = message
    db.commit()


def _estimate_cost(execution: dict[str, Any]) -> float:
    tools = len(execution["tool_calls"])
    llm = sum(1 for e in execution["events"] if "llm" in e["event_type"])
    tiny = sum(1 for e in execution["events"] if e["event_type"].startswith("tinyfish"))
    return tools * COST_PER_TOOL + llm * COST_PER_LLM + tiny * COST_PER_TINYFISH


def _execute_case(
    adapter: TinyFishAdapter, version: AgentVersion, case: TestCase
) -> dict[str, Any]:
    tags = [str(t).lower() for t in (case.tags or [])]
    expected = case.expected_behaviour or {}
    if "tinyfish" in tags or expected.get("agent_url"):
        return _execute_tinyfish_case(adapter, version, case)
    return _execute_support_case(version, case)


def _execute_tinyfish_case(
    adapter: TinyFishAdapter, version: AgentVersion, case: TestCase
) -> dict[str, Any]:
    expected = case.expected_behaviour or {}
    url = expected.get("agent_url") or "https://example.com"
    goal = expected.get("agent_goal") or case.input_text
    scenario = expected.get("scenario") or "happy_path"
    quality = _version_quality(version)
    if scenario == "loop":
        scenario = "forced_loop"

    events: list[dict[str, Any]] = []
    tool_calls: list[str] = []

    def on_event(payload: dict[str, Any], duration_ms: float, status: str) -> None:
        event_name = payload.get("type") or "EVENT"
        events.append(
            {
                "event_type": f"tinyfish.{event_name}",
                "payload": payload,
                "duration_ms": duration_ms,
                "status": status,
            }
        )
        if event_name == "PROGRESS":
            tool_calls.append("tinyfish.navigate")

    search_query = expected.get("search_query")
    if search_query:
        search = adapter.search(search_query)
        events.append(
            {
                "event_type": "tinyfish.search",
                "payload": search,
                "duration_ms": float(search.get("duration_ms") or 0),
                "status": "ok" if search.get("ok") else "error",
            }
        )
        tool_calls.append("tinyfish.search")

    fetch_urls = expected.get("fetch_urls") or ([url] if expected.get("ground_with_fetch") else [])
    fetch_result = None
    if fetch_urls:
        fetch_result = adapter.fetch_pages(
            fetch_urls,
            purpose="Build evaluation ground-truth for AgentOps TinyFish test case",
        )
        events.append(
            {
                "event_type": "tinyfish.fetch",
                "payload": fetch_result,
                "duration_ms": float(fetch_result.get("duration_ms") or 0),
                "status": "ok" if fetch_result.get("ok") else "error",
            }
        )
        tool_calls.append("tinyfish.fetch")

    events.append(
        {
            "event_type": "llm.call",
            "payload": {
                "model": version.model_label,
                "system_prompt_excerpt": version.system_prompt[:280],
                "input": case.input_text,
                "provider_note": "Planner decides TinyFish Agent goal before SSE stream",
            },
            "duration_ms": 90 + (0 if quality > 0.6 else 40),
            "status": "ok",
        }
    )

    agent = adapter.run_agent(
        url,
        goal,
        output_schema=expected.get("output_schema"),
        scenario=scenario,
        on_event=on_event,
        max_steps=int(expected.get("max_steps", 8)),
    )
    result = agent.get("result") or {}
    markdown = ""
    if fetch_result:
        markdown = str(fetch_result.get("markdown") or "")
    output = {
        "ok": agent.get("ok"),
        "status": agent.get("status"),
        "source": "tinyfish",
        "live": agent.get("live"),
        "title": result.get("title") if isinstance(result, dict) else None,
        "price": result.get("price") if isinstance(result, dict) else None,
        "plan": result.get("plan") if isinstance(result, dict) else None,
        "refund_window_days": result.get("refund_window_days") if isinstance(result, dict) else 30,
        "extracted": result,
        "grounded_excerpt": markdown[:400],
        "tinyfish_run_id": agent.get("run_id"),
    }
    if expected.get("inject_unsupported") and quality < 0.7:
        output["price"] = "$0.01"
        output["extracted"] = {**(result if isinstance(result, dict) else {}), "price": "$0.01"}
        output["ok"] = False
    return {"events": events, "tool_calls": tool_calls, "output": output}


def _execute_support_case(version: AgentVersion, case: TestCase) -> dict[str, Any]:
    expected = case.expected_behaviour or {}
    quality = _version_quality(version)
    events: list[dict[str, Any]] = []
    tool_calls: list[str] = []
    t = 42.0

    def llm(name: str, payload: dict[str, Any], status: str = "ok") -> None:
        nonlocal t
        t += 55
        events.append(
            {
                "event_type": name,
                "payload": payload,
                "duration_ms": t,
                "status": status,
            }
        )

    def tool(name: str, payload: dict[str, Any], status: str = "ok") -> None:
        nonlocal t
        t += 35
        tool_calls.append(name)
        events.append(
            {
                "event_type": f"tool.{name}",
                "payload": payload,
                "duration_ms": t,
                "status": status,
            }
        )

    llm(
        "llm.call",
        {
            "model": version.model_label,
            "system_prompt_excerpt": version.system_prompt[:280],
            "input": case.input_text,
        },
    )

    order_id = expected.get("order_id", "ORD-1001")
    order_age = int(expected.get("order_age_days", 12))
    pii = expected.get("foreign_pii")
    expect_refund = bool(expected.get("expect_refund"))
    skip_lookup = quality < 0.55 and expected.get("allow_baseline_skip")

    if skip_lookup:
        llm("llm.retry", {"reason": "Guessing order state without lookup", "retry": True}, "warn")
    else:
        tool(
            "lookup_order",
            {"order_id": order_id, "age_days": order_age, "status": "delivered"},
        )

    policy_ok = order_age <= 30
    if expected.get("needs_policy_lookup") or quality >= 0.6:
        tool(
            "search_policy",
            {
                "query": "refund window",
                "via": "tinyfish.search",
                "result": "Refunds allowed within 30 days of fulfillment.",
            },
        )

    refund_issued = False
    if expect_refund and (policy_ok or quality < 0.5):
        if quality < 0.5 and not policy_ok:
            tool("issue_refund", {"order_id": order_id, "amount": 89.0}, "error")
            refund_issued = True
        elif policy_ok:
            tool("issue_refund", {"order_id": order_id, "amount": expected.get("amount", 89.0)})
            refund_issued = True
    elif not expect_refund and quality < 0.5 and expected.get("baseline_over_refund"):
        tool("issue_refund", {"order_id": order_id, "amount": 89.0}, "error")
        refund_issued = True

    if quality < 0.55 and expected.get("baseline_retries"):
        tool("lookup_order", {"order_id": order_id, "retry": True}, "warn")
        tool("lookup_order", {"order_id": order_id, "retry": True}, "warn")

    answer = expected.get("candidate_answer") if quality >= 0.6 else expected.get("baseline_answer")
    if not answer:
        if refund_issued:
            answer = f"Refund issued for {order_id}."
        elif not expected.get("order_id") and quality >= 0.6:
            answer = "I need the order id before I can look up refund eligibility."
        else:
            answer = (
                "Refund denied: order is outside the 30-day policy window."
                if not policy_ok
                else f"Processed request for {order_id}."
            )

    if pii and quality < 0.6:
        answer += f" Other customer on file: {pii}"

    output = {
        "ok": True,
        "refund_issued": refund_issued,
        "order_id": order_id if expected.get("order_id") or skip_lookup else None,
        "order_age_days": order_age,
        "refund_status": "issued" if refund_issued else "denied",
        "answer": answer,
        "policy_window_days": 30,
    }
    if not expected.get("order_id") and quality >= 0.6:
        output["order_id"] = None
        output["ok"] = True
        output["asked_for_order_id"] = True

    llm("llm.final", {"output": output})
    return {"events": events, "tool_calls": tool_calls, "output": output}


def _version_quality(version: AgentVersion) -> float:
    name = (version.name or "").lower()
    prompt = (version.system_prompt or "").lower()
    score = 0.4
    if "candidate" in name:
        score += 0.35
    if "baseline" in name:
        score -= 0.05
    if "verify" in prompt:
        score += 0.1
    if "30 day" in prompt or "30-day" in prompt:
        score += 0.1
    if "tinyfish" in prompt:
        score += 0.05
    if "never disclose" in prompt or "pii" in prompt:
        score += 0.1
    return min(score, 0.98)
