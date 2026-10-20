from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    versions: Mapped[list["AgentVersion"]] = relationship(back_populates="project")
    suites: Mapped[list["TestSuite"]] = relationship(back_populates="project")


class AgentVersion(Base):
    __tablename__ = "agent_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    model_label: Mapped[str] = mapped_column(String(80), default="gpt-4.1-mini")

    project: Mapped[Project] = relationship(back_populates="versions")
    runs: Mapped[list["Run"]] = relationship(back_populates="version")


class TestSuite(Base):
    __tablename__ = "test_suites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")

    project: Mapped[Project] = relationship(back_populates="suites")
    cases: Mapped[list["TestCase"]] = relationship(back_populates="suite")
    runs: Mapped[list["Run"]] = relationship(back_populates="suite")


class TestCase(Base):
    __tablename__ = "test_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    suite_id: Mapped[int] = mapped_column(ForeignKey("test_suites.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False, default="Untitled case")
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    expected_behaviour: Mapped[dict] = mapped_column(JSON, default=dict)
    reference_data: Mapped[dict | None] = mapped_column(JSON, default=dict)
    tags: Mapped[list] = mapped_column(JSON, default=list)

    suite: Mapped[TestSuite] = relationship(back_populates="cases")
    evaluations: Mapped[list["EvaluationResult"]] = relationship(back_populates="test_case")


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("agent_versions.id"), nullable=False)
    suite_id: Mapped[int] = mapped_column(ForeignKey("test_suites.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="queued")
    pass_rate: Mapped[float] = mapped_column(Float, default=0.0)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    tool_call_count: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    version: Mapped[AgentVersion] = relationship(back_populates="runs")
    suite: Mapped[TestSuite] = relationship(back_populates="runs")
    traces: Mapped[list["TraceEvent"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="TraceEvent.step"
    )
    evaluations: Mapped[list["EvaluationResult"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class TraceEvent(Base):
    __tablename__ = "trace_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), nullable=False)
    test_case_id: Mapped[int | None] = mapped_column(ForeignKey("test_cases.id"), nullable=True)
    step: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(40), default="ok")

    run: Mapped[Run] = relationship(back_populates="traces")


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), nullable=False)
    test_case_id: Mapped[int] = mapped_column(ForeignKey("test_cases.id"), nullable=False)
    assertion_name: Mapped[str] = mapped_column(String(120), nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    taxonomy: Mapped[str | None] = mapped_column(String(80), nullable=True)

    run: Mapped[Run] = relationship(back_populates="evaluations")
    test_case: Mapped[TestCase] = relationship(back_populates="evaluations")


class Comparison(Base):
    __tablename__ = "comparisons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    baseline_run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), nullable=False)
    candidate_run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), nullable=False)
    delta_metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
