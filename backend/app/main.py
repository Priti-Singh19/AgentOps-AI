from __future__ import annotations

from statistics import median
from typing import Any

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.database import SessionLocal, get_db, init_db
from app.models import (
    AgentVersion,
    Comparison,
    EvaluationResult,
    Project,
    Run,
    TestCase,
    TestSuite,
    TraceEvent,
)
from app.runner import execute_run, fail_run
from app.schemas import (
    AgentVersionOut,
    ComparisonCreate,
    ComparisonOut,
    OverviewOut,
    ProjectOut,
    RunCreate,
    RunDetailOut,
    RunOut,
    TestCaseCreate,
    TestCaseOut,
    TestSuiteOut,
)
from app.seed import seed_if_empty, _delta

app = FastAPI(title="AgentOps AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()


def _run_out(run: Run) -> RunOut:
    return RunOut(
        id=run.id,
        version_id=run.version_id,
        suite_id=run.suite_id,
        status=run.status,
        pass_rate=run.pass_rate,
        latency_ms=run.latency_ms,
        tool_call_count=run.tool_call_count,
        cost_usd=run.cost_usd,
        progress=run.progress,
        error_message=run.error_message,
        created_at=run.created_at,
        version_name=run.version.name if run.version else None,
        suite_name=run.suite.name if run.suite else None,
    )


def _execute_in_background(run_id: int) -> None:
    db = SessionLocal()
    try:
        execute_run(db, run_id)
    except Exception as exc:  # noqa: BLE001
        fail_run(db, run_id, str(exc))
    finally:
        db.close()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "agentops-ai"}


@app.get("/api/overview", response_model=OverviewOut)
def overview(db: Session = Depends(get_db)) -> OverviewOut:
    project = db.query(Project).order_by(Project.id.asc()).first()
    if not project:
        raise HTTPException(404, "Project not seeded")
    runs = db.query(Run).options(joinedload(Run.version), joinedload(Run.suite)).all()
    completed = [r for r in runs if r.status == "completed"]
    latencies = [r.latency_ms for r in completed if r.latency_ms]
    pass_rates = [r.pass_rate for r in completed]
    tool_rates = []
    for run in completed:
        case_count = db.query(func.count(TestCase.id)).filter(TestCase.suite_id == run.suite_id).scalar() or 1
        tool_rates.append(run.tool_call_count / max(case_count, 1))
    tinyfish_events = (
        db.query(func.count(TraceEvent.id))
        .filter(TraceEvent.event_type.like("tinyfish%"))
        .scalar()
        or 0
    )
    taxonomy_rows = (
        db.query(EvaluationResult.taxonomy, func.count(EvaluationResult.id))
        .filter(EvaluationResult.passed.is_(False), EvaluationResult.taxonomy.is_not(None))
        .group_by(EvaluationResult.taxonomy)
        .all()
    )
    version_stats: list[dict[str, Any]] = []
    versions = db.query(AgentVersion).filter(AgentVersion.project_id == project.id).all()
    for version in versions:
        vruns = [r for r in completed if r.version_id == version.id]
        version_stats.append(
            {
                "version_id": version.id,
                "name": version.name,
                "runs": len(vruns),
                "pass_rate": round(sum(r.pass_rate for r in vruns) / max(len(vruns), 1), 4),
                "latency_ms": round(sum(r.latency_ms for r in vruns) / max(len(vruns), 1), 2),
                "tool_call_count": round(
                    sum(r.tool_call_count for r in vruns) / max(len(vruns), 1), 2
                ),
                "cost_usd": round(sum(r.cost_usd for r in vruns) / max(len(vruns), 1), 4),
            }
        )
    latest = sorted(runs, key=lambda r: r.created_at, reverse=True)[:8]
    return OverviewOut(
        project=ProjectOut.model_validate(project),
        total_runs=len(runs),
        completed_runs=len(completed),
        pass_rate=round(sum(pass_rates) / max(len(pass_rates), 1), 4),
        median_latency_ms=round(median(latencies), 2) if latencies else 0.0,
        tool_calls_per_task=round(sum(tool_rates) / max(len(tool_rates), 1), 2),
        estimated_cost_usd=round(sum(r.cost_usd for r in completed), 4),
        tinyfish_events=int(tinyfish_events),
        latest_runs=[_run_out(r) for r in latest],
        taxonomy_counts={name: int(count) for name, count in taxonomy_rows},
        version_stats=version_stats,
    )


@app.get("/api/projects", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)) -> list[Project]:
    return db.query(Project).all()


@app.get("/api/versions", response_model=list[AgentVersionOut])
def list_versions(db: Session = Depends(get_db)) -> list[AgentVersion]:
    return db.query(AgentVersion).order_by(AgentVersion.id.asc()).all()


@app.get("/api/suites", response_model=list[TestSuiteOut])
def list_suites(db: Session = Depends(get_db)) -> list[TestSuite]:
    return (
        db.query(TestSuite)
        .options(joinedload(TestSuite.cases))
        .order_by(TestSuite.id.asc())
        .all()
    )


@app.post("/api/suites/{suite_id}/cases", response_model=TestCaseOut)
def create_case(suite_id: int, payload: TestCaseCreate, db: Session = Depends(get_db)) -> TestCase:
    suite = db.get(TestSuite, suite_id)
    if not suite:
        raise HTTPException(404, "Suite not found")
    case = TestCase(
        suite_id=suite_id,
        name=payload.name,
        input_text=payload.input_text,
        expected_behaviour=payload.expected_behaviour,
        reference_data=payload.reference_data,
        tags=payload.tags,
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


@app.get("/api/runs", response_model=list[RunOut])
def list_runs(db: Session = Depends(get_db)) -> list[RunOut]:
    runs = (
        db.query(Run)
        .options(joinedload(Run.version), joinedload(Run.suite))
        .order_by(Run.id.desc())
        .all()
    )
    return [_run_out(r) for r in runs]


@app.post("/api/runs", response_model=RunOut)
def start_run(
    payload: RunCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> RunOut:
    version = db.get(AgentVersion, payload.version_id)
    suite = db.get(TestSuite, payload.suite_id)
    if not version or not suite:
        raise HTTPException(404, "Version or suite not found")
    run = Run(version_id=version.id, suite_id=suite.id, status="queued")
    db.add(run)
    db.commit()
    db.refresh(run)
    run.version = version
    run.suite = suite
    background_tasks.add_task(_execute_in_background, run.id)
    return _run_out(run)


@app.get("/api/runs/{run_id}", response_model=RunDetailOut)
def get_run(run_id: int, db: Session = Depends(get_db)) -> RunDetailOut:
    run = (
        db.query(Run)
        .options(
            joinedload(Run.version),
            joinedload(Run.suite),
            joinedload(Run.traces),
            joinedload(Run.evaluations),
        )
        .filter(Run.id == run_id)
        .first()
    )
    if not run:
        raise HTTPException(404, "Run not found")
    base = _run_out(run)
    return RunDetailOut(
        **base.model_dump(),
        traces=sorted(run.traces, key=lambda item: item.step),
        evaluations=run.evaluations,
    )


@app.get("/api/comparisons", response_model=list[ComparisonOut])
def list_comparisons(db: Session = Depends(get_db)) -> list[Comparison]:
    return db.query(Comparison).order_by(Comparison.id.desc()).all()


@app.post("/api/comparisons", response_model=ComparisonOut)
def create_comparison(payload: ComparisonCreate, db: Session = Depends(get_db)) -> Comparison:
    baseline = db.get(Run, payload.baseline_run_id)
    candidate = db.get(Run, payload.candidate_run_id)
    if not baseline or not candidate:
        raise HTTPException(404, "Runs not found")
    row = Comparison(
        baseline_run_id=baseline.id,
        candidate_run_id=candidate.id,
        delta_metrics=_delta(baseline, candidate),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
