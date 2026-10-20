from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProjectOut(ORMModel):
    id: int
    name: str
    created_at: datetime


class AgentVersionOut(ORMModel):
    id: int
    project_id: int
    name: str
    system_prompt: str
    model_label: str


class TestCaseCreate(BaseModel):
    name: str
    input_text: str
    expected_behaviour: dict[str, Any] = Field(default_factory=dict)
    reference_data: dict[str, Any] | None = None
    tags: list[Any] = Field(default_factory=list)


class TestCaseOut(ORMModel):
    id: int
    suite_id: int
    name: str
    input_text: str
    expected_behaviour: dict[str, Any] = Field(default_factory=dict)
    reference_data: dict[str, Any] | None = None
    tags: list[Any] = Field(default_factory=list)


class TestSuiteOut(ORMModel):
    id: int
    project_id: int
    name: str
    description: str = ""
    cases: list[TestCaseOut] = Field(default_factory=list)


class TraceEventOut(ORMModel):
    id: int
    run_id: int
    test_case_id: int | None = None
    step: int
    event_type: str
    payload: dict[str, Any]
    duration_ms: float
    status: str


class EvaluationOut(ORMModel):
    id: int
    run_id: int
    test_case_id: int
    assertion_name: str
    passed: bool
    score: float
    failure_reason: str | None = None
    taxonomy: str | None = None


class RunOut(ORMModel):
    id: int
    version_id: int
    suite_id: int
    status: str
    pass_rate: float
    latency_ms: float
    tool_call_count: int
    cost_usd: float
    progress: int
    error_message: str | None = None
    created_at: datetime
    version_name: str | None = None
    suite_name: str | None = None


class RunDetailOut(RunOut):
    traces: list[TraceEventOut] = Field(default_factory=list)
    evaluations: list[EvaluationOut] = Field(default_factory=list)


class RunCreate(BaseModel):
    version_id: int
    suite_id: int


class ComparisonCreate(BaseModel):
    baseline_run_id: int
    candidate_run_id: int


class ComparisonOut(ORMModel):
    id: int
    baseline_run_id: int
    candidate_run_id: int
    delta_metrics: dict[str, Any]
    created_at: datetime


class OverviewOut(BaseModel):
    project: ProjectOut
    total_runs: int
    completed_runs: int
    pass_rate: float
    median_latency_ms: float
    tool_calls_per_task: float
    estimated_cost_usd: float
    tinyfish_events: int
    latest_runs: list[RunOut]
    taxonomy_counts: dict[str, int]
    version_stats: list[dict[str, Any]]
