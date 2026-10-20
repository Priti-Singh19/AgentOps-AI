"""TinyFish Agent, Fetch, and Search adapters.

Live calls use TINYFISH_API_KEY. When the key is missing or a request fails,
the adapter emits the same TinyFish event schema so AgentOps traces stay
inspectable during local/hackathon demos.
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable, Iterator
from typing import Any
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv

load_dotenv()

AGENT_BASE = os.getenv("TINYFISH_AGENT_BASE", "https://agent.tinyfish.ai")
FETCH_URL = os.getenv("TINYFISH_FETCH_URL", "https://api.fetch.tinyfish.ai")
SEARCH_URL = os.getenv("TINYFISH_SEARCH_URL", "https://api.search.tinyfish.ai")


EventCallback = Callable[[dict[str, Any], float, str], None]


class TinyFishAdapter:
    """Wraps TinyFish Agent SSE, Fetch, and Search APIs."""

    def __init__(self, api_key: str | None = None, timeout: float = 90.0) -> None:
        self.api_key = api_key or os.getenv("TINYFISH_API_KEY") or ""
        self.timeout = timeout

    @property
    def enabled(self) -> bool:
        return bool(self.api_key.strip())

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def fetch_pages(
        self,
        urls: list[str],
        *,
        fmt: str = "markdown",
        purpose: str = "Ground AgentOps evaluation against live web policy content",
        links: bool = False,
    ) -> dict[str, Any]:
        """Fetch live pages via TinyFish Fetch API and return markdown/JSON text."""
        started = time.perf_counter()
        payload = {
            "urls": urls,
            "format": fmt,
            "links": links,
            "purpose": purpose,
            "ttl": 0,
        }
        if self.enabled:
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(FETCH_URL, headers=self._headers(), json=payload)
                    duration = (time.perf_counter() - started) * 1000
                    body = _safe_json(response)
                    return {
                        "source": "tinyfish.fetch",
                        "ok": response.is_success,
                        "status_code": response.status_code,
                        "duration_ms": duration,
                        "request": payload,
                        "response": body,
                        "markdown": _extract_fetch_text(body),
                    }
            except httpx.HTTPError as exc:
                duration = (time.perf_counter() - started) * 1000
                return {
                    "source": "tinyfish.fetch",
                    "ok": False,
                    "status_code": None,
                    "duration_ms": duration,
                    "request": payload,
                    "error": str(exc),
                    "markdown": "",
                }
        return self._simulate_fetch(urls, fmt, purpose, started)

    def search(
        self,
        query: str,
        *,
        location: str = "US",
        language: str = "en",
        purpose: str = "Find grounding documents for AgentOps evaluation",
    ) -> dict[str, Any]:
        started = time.perf_counter()
        params = {
            "query": query,
            "location": location,
            "language": language,
            "purpose": purpose,
        }
        if self.enabled:
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.get(
                        SEARCH_URL, headers=self._headers(), params=params
                    )
                    duration = (time.perf_counter() - started) * 1000
                    body = _safe_json(response)
                    return {
                        "source": "tinyfish.search",
                        "ok": response.is_success,
                        "status_code": response.status_code,
                        "duration_ms": duration,
                        "request": params,
                        "response": body,
                    }
            except httpx.HTTPError as exc:
                duration = (time.perf_counter() - started) * 1000
                return {
                    "source": "tinyfish.search",
                    "ok": False,
                    "duration_ms": duration,
                    "request": params,
                    "error": str(exc),
                }
        return self._simulate_search(query, params, started)

    def run_agent(
        self,
        url: str,
        goal: str,
        *,
        output_schema: dict[str, Any] | None = None,
        scenario: str = "happy_path",
        on_event: EventCallback | None = None,
        max_steps: int = 12,
    ) -> dict[str, Any]:
        """Execute a web-agent goal and stream TinyFish events into traces."""
        body: dict[str, Any] = {
            "url": url,
            "goal": goal,
            "browser_profile": "lite",
        }
        if output_schema:
            body["output_schema"] = output_schema

        if self.enabled and scenario != "forced_loop":
            return self._run_agent_sse(body, on_event)

        return self._simulate_agent(
            url, goal, scenario=scenario, on_event=on_event, max_steps=max_steps
        )

    def _run_agent_sse(
        self, payload: dict[str, Any], on_event: EventCallback | None
    ) -> dict[str, Any]:
        endpoint = f"{AGENT_BASE.rstrip('/')}/v1/automation/run-sse"
        events: list[dict[str, Any]] = []
        final: dict[str, Any] = {
            "source": "tinyfish.agent.sse",
            "ok": False,
            "result": None,
            "error": None,
            "status": "FAILED",
            "num_of_steps": 0,
            "events": events,
            "live": True,
        }
        started = time.perf_counter()
        try:
            with httpx.Client(timeout=self.timeout) as client:
                with client.stream(
                    "POST", endpoint, headers=self._headers(), json=payload
                ) as response:
                    if response.status_code >= 400:
                        duration = (time.perf_counter() - started) * 1000
                        err = _safe_json(response)
                        final["error"] = err
                        final["status_code"] = response.status_code
                        if on_event:
                            on_event(
                                {
                                    "provider": "tinyfish",
                                    "type": "COMPLETE",
                                    "status": "FAILED",
                                    "error": err,
                                    "live": True,
                                },
                                duration,
                                "error",
                            )
                        return final
                    for line in response.iter_lines():
                        if not line:
                            continue
                        text = line.decode() if isinstance(line, bytes) else line
                        if not text.startswith("data:"):
                            continue
                        raw = text[5:].strip()
                        if not raw:
                            continue
                        try:
                            event = json.loads(raw)
                        except json.JSONDecodeError:
                            continue
                        event["provider"] = "tinyfish"
                        event["live"] = True
                        events.append(event)
                        elapsed = (time.perf_counter() - started) * 1000
                        status = "ok"
                        if event.get("type") == "COMPLETE" and event.get("status") == "FAILED":
                            status = "error"
                        if on_event:
                            on_event(event, elapsed, status)
                        if event.get("type") == "COMPLETE":
                            final["ok"] = event.get("status") == "COMPLETED"
                            final["status"] = event.get("status", "FAILED")
                            final["result"] = event.get("result")
                            final["error"] = event.get("error")
                            final["run_id"] = event.get("run_id")
        except httpx.HTTPError as exc:
            duration = (time.perf_counter() - started) * 1000
            final["error"] = {"message": str(exc), "code": "HTTP_ERROR"}
            if on_event:
                on_event(
                    {
                        "provider": "tinyfish",
                        "type": "COMPLETE",
                        "status": "FAILED",
                        "error": final["error"],
                        "live": True,
                    },
                    duration,
                    "error",
                )
        final["num_of_steps"] = len(
            [e for e in events if e.get("type") in {"PROGRESS", "STARTED"}]
        )
        return final

    def _simulate_fetch(
        self, urls: list[str], fmt: str, purpose: str, started: float
    ) -> dict[str, Any]:
        pages = []
        for url in urls:
            host = urlparse(url).netloc or "example.com"
            markdown = (
                f"# Grounding document from {host}\n\n"
                "Refunds are allowed within **30 days** of purchase when the order "
                "is verified. After 30 days, refunds are denied. Agents must never "
                "disclose another customer's PII. Extracted fields should include "
                "title, price, and plan details when scraping marketing pages.\n"
            )
            pages.append({"url": url, "format": fmt, "text": markdown, "ok": True})
        duration = max((time.perf_counter() - started) * 1000, 12.0)
        return {
            "source": "tinyfish.fetch",
            "ok": True,
            "status_code": 200,
            "duration_ms": duration,
            "live": False,
            "mode": "simulated",
            "request": {"urls": urls, "format": fmt, "purpose": purpose},
            "response": {"results": pages},
            "markdown": "\n\n".join(p["text"] for p in pages),
        }

    def _simulate_search(
        self, query: str, params: dict[str, Any], started: float
    ) -> dict[str, Any]:
        duration = max((time.perf_counter() - started) * 1000, 18.0)
        return {
            "source": "tinyfish.search",
            "ok": True,
            "live": False,
            "mode": "simulated",
            "duration_ms": duration,
            "request": params,
            "response": {
                "query": query,
                "total_results": 2,
                "results": [
                    {
                        "title": "Refund policy — 30 day window",
                        "url": "https://example.com/refund-policy",
                        "snippet": "Customers may request a refund within 30 days of order fulfillment.",
                    },
                    {
                        "title": "TinyFish web agent extraction guide",
                        "url": "https://docs.tinyfish.ai/agent-api/reference",
                        "snippet": "Stream STARTED, PROGRESS, and COMPLETE events from /run-sse.",
                    },
                ],
            },
        }

    def _simulate_agent(
        self,
        url: str,
        goal: str,
        *,
        scenario: str,
        on_event: EventCallback | None,
        max_steps: int,
    ) -> dict[str, Any]:
        host = urlparse(url).netloc or url
        run_id = f"tf_sim_{int(time.time() * 1000)}"
        events: list[dict[str, Any]] = []
        t0 = time.perf_counter()

        def emit(event: dict[str, Any], status: str = "ok") -> None:
            event.setdefault("provider", "tinyfish")
            event.setdefault("run_id", run_id)
            event.setdefault("live", False)
            event.setdefault("mode", "simulated")
            events.append(event)
            elapsed = (time.perf_counter() - t0) * 1000 + len(events) * 40
            if on_event:
                on_event(event, elapsed, status)
            time.sleep(0.012)

        emit({"type": "STARTED", "timestamp": _ts(), "url": url, "goal": goal})
        emit(
            {
                "type": "STREAMING_URL",
                "streaming_url": f"https://agent.tinyfish.ai/streams/{run_id}",
                "timestamp": _ts(),
            }
        )

        if scenario == "forced_loop":
            for i in range(max(max_steps, 6)):
                emit(
                    {
                        "type": "PROGRESS",
                        "purpose": f"Navigating {host}/checkout (repeat {i + 1})",
                        "action": "navigate",
                        "selector": "a.checkout",
                        "timestamp": _ts(),
                    },
                    "warn",
                )
            result = {"extracted": None, "loop_detected": True}
            emit(
                {
                    "type": "COMPLETE",
                    "status": "FAILED",
                    "result": result,
                    "error": {
                        "code": "MAX_STEPS_EXCEEDED",
                        "message": "Agent repeated the same navigation without progress",
                    },
                    "timestamp": _ts(),
                },
                "error",
            )
            return {
                "source": "tinyfish.agent.sse",
                "ok": False,
                "live": False,
                "status": "FAILED",
                "result": result,
                "error": {"code": "MAX_STEPS_EXCEEDED"},
                "num_of_steps": len(events),
                "events": events,
                "run_id": run_id,
            }

        steps = [
            f"Opening {url}",
            "Waiting for DOM content",
            "Extracting visible text via TinyFish Fetch grounding",
            "Normalizing tables and prices",
            "Validating output schema",
        ]
        for purpose in steps:
            emit({"type": "PROGRESS", "purpose": purpose, "timestamp": _ts()})

        extracted = {
            "title": f"Example site {host}",
            "price": "$799",
            "plan": "Pro",
            "refund_window_days": 30,
            "source_url": url,
            "goal": goal,
        }
        emit(
            {
                "type": "COMPLETE",
                "status": "COMPLETED",
                "result": extracted,
                "timestamp": _ts(),
            }
        )
        return {
            "source": "tinyfish.agent.sse",
            "ok": True,
            "live": False,
            "status": "COMPLETED",
            "result": extracted,
            "error": None,
            "num_of_steps": len(events),
            "events": events,
            "run_id": run_id,
        }


def _safe_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except Exception:
        return {"raw": response.text[:4000], "status_code": response.status_code}


def _extract_fetch_text(body: Any) -> str:
    if not isinstance(body, dict):
        return str(body)
    results = body.get("results") or body.get("data") or []
    chunks: list[str] = []
    if isinstance(results, list):
        for item in results:
            if isinstance(item, dict):
                text = item.get("text") or item.get("markdown") or item.get("content")
                if text:
                    chunks.append(str(text))
    if not chunks and body.get("text"):
        chunks.append(str(body["text"]))
    return "\n\n".join(chunks)


def _ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def iter_sse_payloads(raw_lines: Iterator[str]) -> Iterator[dict[str, Any]]:
    for line in raw_lines:
        if line.startswith("data:"):
            blob = line[5:].strip()
            if blob:
                yield json.loads(blob)
