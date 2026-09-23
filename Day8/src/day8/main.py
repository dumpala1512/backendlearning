from __future__ import annotations

import asyncio
from pathlib import Path
import sys

# Allow running this script directly
if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from day8.models import Job, Priority
from day8.processor import run_batch


def sample_jobs() -> list[Job]:
    """Create a sample batch of jobs with different priorities, durations, and outcomes."""
    return [
        # Fast High Priority (~0.25s)
        Job("JOB-1", "vip_lookup", Priority.HIGH, {"user_id": 101}),
        Job("JOB-2", "fraud_check", Priority.HIGH, {"amount": 500}),
        Job("JOB-3", "kyc_verify", Priority.HIGH, {"user_id": 102}),
        Job("JOB-4", "audit_log", Priority.HIGH, {"session": "abc"}),

        # Medium Priority (~0.60s)
        Job("JOB-5", "credit_score", Priority.MEDIUM, {"ssn": "1234"}),
        Job("JOB-6", "tax_check", Priority.MEDIUM, {"tax_id": "T-99"}),
        Job("JOB-7", "sanctions", Priority.MEDIUM, {"name": "Acme Corp"}),
        Job("JOB-8", "address_lookup", Priority.MEDIUM, {"zip": "94105"}),

        # Low Priority (~1.10s)
        Job("JOB-9", "archive_sync", Priority.LOW, {"ledger": "L1"}, simulated_duration=0.8),
        Job("JOB-10", "report_generate", Priority.LOW, {"year": 2025}, simulated_duration=0.8),

        # Failure test cases:
        # Times out because duration (2.0s) > per_job_timeout (1.0s)
        Job("JOB-11", "slow_partner_api", Priority.LOW, {}, simulated_duration=2.0),
        # Fails with RuntimeError
        Job("JOB-12", "payment_gateway", Priority.MEDIUM, {}, should_fail=True),
    ]


async def async_main() -> None:
    jobs = sample_jobs()
    max_concurrency = 4
    per_job_timeout = 1.0

    print("=" * 60)
    print("      NIGHTLY ASYNC BATCH JOB PROCESSOR")
    print("=" * 60)
    print(f"Total Jobs to Process : {len(jobs)}")
    print(f"Max Concurrency       : {max_concurrency} parallel workers")
    print(f"Per-Job Timeout       : {per_job_timeout} seconds\n")

    print("[*] Processing batch...")
    summary = await run_batch(jobs, max_concurrency=max_concurrency, per_job_timeout=per_job_timeout)

    print("\n--- RESULTS ---")
    for r in summary.results:
        status = "SUCCESS" if r.success else f"FAILED ({r.error_reason})"
        print(f"  {r.job_id:<8} | {status:<24} | Took {r.duration_seconds:.2f}s")

    print("\n" + "=" * 60)
    print("      BATCH RUN SUMMARY")
    print("=" * 60)
    print(f"  Total Jobs             : {summary.total_jobs}")
    print(f"  Successful             : {summary.successful_count}")
    print(f"  Failed                 : {summary.failed_count} ({summary.failure_breakdown})")
    print(f"  Sequential Time (est)  : {summary.sequential_equivalent_time:.2f}s")
    print(f"  Concurrent Wall Time   : {summary.total_wall_clock_time:.2f}s")
    print(f"  Speedup Factor         : {summary.speedup_factor:.2f}x faster!")
    print("=" * 60)


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
