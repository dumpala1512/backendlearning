from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class Priority:
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class Job:
    """Represents a single enrichment job."""
    id: str
    job_type: str
    priority: str
    payload: Any
    simulated_duration: float | None = None
    should_fail: bool = False


@dataclass
class JobResult:
    """The result of running a single job."""
    job_id: str
    success: bool
    duration_seconds: float
    data: Any = None
    error_reason: str | None = None


@dataclass
class BatchSummary:
    """Run summary showing performance and results."""
    total_jobs: int
    successful_count: int
    failed_count: int
    failure_breakdown: dict[str, int] = field(default_factory=dict)
    total_wall_clock_time: float = 0.0
    sequential_equivalent_time: float = 0.0
    speedup_factor: float = 0.0
    results: list[JobResult] = field(default_factory=list)
