from __future__ import annotations

import asyncio
from collections import defaultdict
import time

from day8.models import BatchSummary, Job, JobResult, Priority

# Default simulated I/O wait times based on priority
PRIORITY_SPEEDS = {
    Priority.HIGH: 0.25,
    Priority.MEDIUM: 0.60,
    Priority.LOW: 1.10,
}


async def process_single_job(job: Job, per_job_timeout: float = 1.0) -> JobResult:
    """Process a single job with simulated I/O and a strict timeout."""
    start = time.perf_counter()                       #start the timer 
    duration = job.simulated_duration or PRIORITY_SPEEDS.get(job.priority, 0.5)

    try:
        # Cancel job if it takes longer than per_job_timeout
        async with asyncio.timeout(per_job_timeout):
            await asyncio.sleep(duration)                 #waiting time process happens here  

            if job.should_fail:
                raise RuntimeError("ServiceConnectionError")

        elapsed = time.perf_counter() - start              #stop the timer
        return JobResult(
            job_id=job.id,
            success=True,
            duration_seconds=round(elapsed, 2),
            data={"status": "enriched", "job_type": job.job_type},
        )

    except TimeoutError:
        elapsed = time.perf_counter() - start
        return JobResult(
            job_id=job.id,
            success=False,
            duration_seconds=round(elapsed, 2),
            error_reason="TIMEOUT",
        )

    except Exception as exc:
        elapsed = time.perf_counter() - start
        return JobResult(
            job_id=job.id,
            success=False,
            duration_seconds=round(elapsed, 2),
            error_reason=type(exc).__name__,
        )


async def run_batch(
    jobs: list[Job],
    max_concurrency: int = 4,
    per_job_timeout: float = 1.0,
) -> BatchSummary:
    """Run a batch of jobs concurrently with a maximum concurrency limit."""
    if not jobs:
        return BatchSummary(0, 0, 0)

    # Semaphore ensures no more than max_concurrency jobs run at the exact same time
    semaphore = asyncio.Semaphore(max_concurrency)

    async def worker(job: Job) -> JobResult:
        async with semaphore:
            return await process_single_job(job, per_job_timeout=per_job_timeout)

    batch_start = time.perf_counter()

    # Dispatch all jobs concurrently
    results = await asyncio.gather(*(worker(job) for job in jobs))

    total_wall_time = time.perf_counter() - batch_start

    # Tally metrics
    successes = sum(1 for r in results if r.success)
    failures = len(results) - successes
    seq_time = sum(r.duration_seconds for r in results)
    speedup = seq_time / total_wall_time if total_wall_time > 0 else 1.0

    breakdown = defaultdict(int)
    for r in results:
        if not r.success and r.error_reason:
            breakdown[r.error_reason] += 1

    return BatchSummary(
        total_jobs=len(jobs),
        successful_count=successes,
        failed_count=failures,
        failure_breakdown=dict(breakdown),
        total_wall_clock_time=round(total_wall_time, 2),
        sequential_equivalent_time=round(seq_time, 2),
        speedup_factor=round(speedup, 2),
        results=results,
    )
