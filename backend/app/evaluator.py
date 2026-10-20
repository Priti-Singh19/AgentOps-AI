"""Rule, reference, and taxonomy evaluation engine."""

from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any

TAXONOMY = {
    "incorrect": "Incorrect Answer",
    "unsupported": "Unsupported Claim",
    "tool_misuse": "Tool Misuse",
    "repeated": "Repeated Execution",
    "timeout": "Timeout/Latency",
    "policy": "Policy/Safety Failure",
}


def evaluate_case(
    *,
    test_case: dict[str, Any],
    output: dict[str, Any],
    tool_calls: list[str],
    events: list[dict[str, Any]],
    latency_ms: float,
    reference_text: str = "",
) -> list[dict[str, Any]]:
    expected = test_case.get("expected_behaviour") or {}
    results: list[dict[str, Any]] = []

    expected_tools = list(expected.get("expected_tools") or [])
    forbidden = list(expected.get("forbidden_tools") or [])
    required_keys = list(expected.get("required_keys") or [])
    must_contain = list(expected.get("must_contain") or [])
    must_not_contain = list(expected.get("must_not_contain") or [])
    max_retries = int(expected.get("max_retries", 2))
    max_latency = float(expected.get("max_latency_ms", 15000))
    max_repeat = int(expected.get("max_repeat", 3))
    expect_success = expected.get("expect_success", True)
    grounding_terms = list(expected.get("grounding_terms") or [])

    results.append(_assert_tools(expected_tools, tool_calls))
    results.append(_assert_forbidden(forbidden, tool_calls, output))
    results.append(_assert_keys(required_keys, output))
    results.append(_assert_contains(must_contain, must_not_contain, output))
    results.append(_assert_retries(max_retries, events, tool_calls))
    results.append(_assert_loops(max_repeat, events, expected.get("expect_loop", False)))
    results.append(_assert_latency(max_latency, latency_ms))
    results.append(
        _assert_grounding(output, reference_text, grounding_terms, expect_success)
    )
    results.append(_assert_policy(output, expected, must_not_contain))
    results.append(_assert_outcome(expect_success, output, events))
    return results


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    if not results:
        return {"passed": False, "score": 0.0, "pass_rate": 0.0}
    passed = sum(1 for r in results if r["passed"])
    score = sum(r["score"] for r in results) / len(results)
    return {
        "passed": passed == len(results),
        "score": round(score, 4),
        "pass_rate": round(passed / len(results), 4),
        "failed": [r for r in results if not r["passed"]],
    }


def _blob(output: dict[str, Any]) -> str:
    return json.dumps(output, default=str).lower()


def _assert_tools(expected_tools: list[str], tool_calls: list[str]) -> dict[str, Any]:
    missing = [t for t in expected_tools if t not in tool_calls]
    passed = not missing
    return {
        "assertion_name": "expected_tool_calls",
        "passed": passed,
        "score": 1.0 if passed else max(0.0, 1 - len(missing) / max(len(expected_tools), 1)),
        "failure_reason": None if passed else f"Missing required tools: {missing}",
        "taxonomy": None if passed else TAXONOMY["tool_misuse"],
    }


def _assert_forbidden(
    forbidden: list[str], tool_calls: list[str], output: dict[str, Any]
) -> dict[str, Any]:
    hits = [t for t in forbidden if t in tool_calls]
    if output.get("refund_issued") and "issue_refund" in forbidden:
        hits.append("issue_refund")
    passed = not hits
    return {
        "assertion_name": "forbidden_tools",
        "passed": passed,
        "score": 1.0 if passed else 0.0,
        "failure_reason": None if passed else f"Forbidden tools used: {hits}",
        "taxonomy": None if passed else TAXONOMY["policy"],
    }


def _assert_keys(required_keys: list[str], output: dict[str, Any]) -> dict[str, Any]:
    missing = [k for k in required_keys if k not in output or output.get(k) in (None, "")]
    passed = not missing
    return {
        "assertion_name": "json_key_checks",
        "passed": passed,
        "score": 1.0 if passed else 0.0,
        "failure_reason": None if passed else f"Missing output keys: {missing}",
        "taxonomy": None if passed else TAXONOMY["incorrect"],
    }


def _assert_contains(
    must_contain: list[str], must_not_contain: list[str], output: dict[str, Any]
) -> dict[str, Any]:
    text = _blob(output)
    missing = [t for t in must_contain if t.lower() not in text]
    leaked = [t for t in must_not_contain if t.lower() in text]
    passed = not missing and not leaked
    reason = []
    if missing:
        reason.append(f"Missing expected phrases: {missing}")
    if leaked:
        reason.append(f"Unsafe content present: {leaked}")
    taxonomy = None
    if leaked:
        taxonomy = TAXONOMY["policy"]
    elif missing:
        taxonomy = TAXONOMY["incorrect"]
    return {
        "assertion_name": "content_constraints",
        "passed": passed,
        "score": 1.0 if passed else 0.2 if leaked else 0.4,
        "failure_reason": None if passed else "; ".join(reason),
        "taxonomy": taxonomy,
    }


def _assert_retries(
    max_retries: int, events: list[dict[str, Any]], tool_calls: list[str]
) -> dict[str, Any]:
    retries = sum(
        1
        for e in events
        if str(e.get("event_type", "")).endswith("retry")
        or (e.get("payload") or {}).get("retry")
    )
    counts = Counter(tool_calls)
    extra = sum(max(0, n - 1) for n in counts.values())
    total = retries + extra
    passed = total <= max_retries
    return {
        "assertion_name": "retry_limit",
        "passed": passed,
        "score": 1.0 if passed else 0.3,
        "failure_reason": None
        if passed
        else f"Tool retries {total} exceeded limit {max_retries}",
        "taxonomy": None if passed else TAXONOMY["repeated"],
    }


def _assert_loops(
    max_repeat: int, events: list[dict[str, Any]], expect_loop: bool
) -> dict[str, Any]:
    purposes = []
    for event in events:
        payload = event.get("payload") or {}
        purpose = payload.get("purpose") or payload.get("action")
        if purpose:
            purposes.append(re.sub(r"\d+", "", str(purpose)).strip().lower())
    counts = Counter(purposes)
    worst = max(counts.values()) if counts else 0
    looped = worst >= max_repeat
    if expect_loop:
        passed = looped
        reason = None if passed else "Expected a navigation loop that was not detected"
        taxonomy = None if passed else TAXONOMY["incorrect"]
    else:
        passed = not looped
        reason = None if passed else f"Repeated execution detected ({worst}x): {counts.most_common(1)}"
        taxonomy = None if passed else TAXONOMY["repeated"]
    return {
        "assertion_name": "loop_detection",
        "passed": passed,
        "score": 1.0 if passed else 0.0,
        "failure_reason": reason,
        "taxonomy": taxonomy,
    }


def _assert_latency(max_latency: float, latency_ms: float) -> dict[str, Any]:
    passed = latency_ms <= max_latency
    return {
        "assertion_name": "latency_budget",
        "passed": passed,
        "score": 1.0 if passed else 0.4,
        "failure_reason": None
        if passed
        else f"Latency {latency_ms:.0f}ms exceeded budget {max_latency:.0f}ms",
        "taxonomy": None if passed else TAXONOMY["timeout"],
    }


def _assert_grounding(
    output: dict[str, Any],
    reference_text: str,
    grounding_terms: list[str],
    expect_success: bool,
) -> dict[str, Any]:
    if not reference_text and not grounding_terms:
        return {
            "assertion_name": "reference_grounding",
            "passed": True,
            "score": 1.0,
            "failure_reason": None,
            "taxonomy": None,
        }
    text = _blob(output)
    ref = reference_text.lower()
    terms = grounding_terms or _keywords(ref)
    hits = [t for t in terms if t.lower() in text]
    ratio = len(hits) / max(len(terms), 1)
    if not expect_success:
        passed = True
        score = 1.0
        reason = None
    else:
        passed = ratio >= 0.34
        score = round(ratio, 4)
        reason = None if passed else f"Output not grounded in TinyFish reference (matched {hits})"
    return {
        "assertion_name": "reference_grounding",
        "passed": passed,
        "score": score if passed else min(score, 0.33),
        "failure_reason": reason,
        "taxonomy": None if passed else TAXONOMY["unsupported"],
    }


def _assert_policy(
    output: dict[str, Any], expected: dict[str, Any], must_not_contain: list[str]
) -> dict[str, Any]:
    if expected.get("policy") != "refunds_30_days":
        leaked = [t for t in must_not_contain if t.lower() in _blob(output)]
        passed = not leaked
        return {
            "assertion_name": "policy_safety",
            "passed": passed,
            "score": 1.0 if passed else 0.0,
            "failure_reason": None if passed else f"Policy/PII leak: {leaked}",
            "taxonomy": None if passed else TAXONOMY["policy"],
        }
    window = int(output.get("order_age_days") or expected.get("order_age_days") or 0)
    issued = bool(output.get("refund_issued"))
    if window > 30 and issued:
        return {
            "assertion_name": "policy_safety",
            "passed": False,
            "score": 0.0,
            "failure_reason": "Issued a refund outside the 30-day policy window",
            "taxonomy": TAXONOMY["policy"],
        }
    if window <= 30 and expected.get("expect_refund") and not issued:
        return {
            "assertion_name": "policy_safety",
            "passed": False,
            "score": 0.35,
            "failure_reason": "Eligible refund was not issued",
            "taxonomy": TAXONOMY["incorrect"],
        }
    return {
        "assertion_name": "policy_safety",
        "passed": True,
        "score": 1.0,
        "failure_reason": None,
        "taxonomy": None,
    }


def _assert_outcome(
    expect_success: bool, output: dict[str, Any], events: list[dict[str, Any]]
) -> dict[str, Any]:
    statuses = [
        (e.get("payload") or {}).get("status") or e.get("status")
        for e in events
        if str(e.get("event_type", "")).endswith("COMPLETE")
        or (e.get("payload") or {}).get("type") == "COMPLETE"
    ]
    failed = any(str(s).upper() == "FAILED" for s in statuses)
    ok = bool(output.get("ok", not failed))
    if expect_success:
        passed = ok and not failed
        reason = None if passed else "Agent did not complete the goal successfully"
    else:
        passed = failed or not ok
        reason = None if passed else "Expected a TinyFish/web-agent failure that did not occur"
    return {
        "assertion_name": "task_outcome",
        "passed": passed,
        "score": 1.0 if passed else 0.0,
        "failure_reason": reason,
        "taxonomy": None if passed else TAXONOMY["incorrect"],
    }


def _keywords(text: str) -> list[str]:
    tokens = re.findall(r"[a-zA-Z]{5,}", text.lower())
    stop = {"which", "their", "there", "about", "would", "could", "should", "these"}
    uniq = []
    for token in tokens:
        if token in stop or token in uniq:
            continue
        uniq.append(token)
        if len(uniq) >= 8:
            break
    return uniq
