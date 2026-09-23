# Day 8: Async/Await, the Event Loop & Batch Job Processor

This module implements the **Async Batch Job Processor** standalone exercise, applying the foundational asynchronous I/O and event loop concepts learned in `Async I/O Importance`.

---

## 1. Concepts from the Learning Notes Applied

| Concept from Notes | Why It Matters | How It Is Implemented in Code |
| :--- | :--- | :--- |
| **Sync vs. Async** | Synchronous execution blocks the entire thread during I/O wait. Async yields control so other tasks make progress. | Nightly batch jobs wait on simulated external APIs using non-blocking `await asyncio.sleep()`. |
| **The Event Loop & `asyncio.run()`** | The central scheduler managing coroutine execution and I/O callbacks. | `main()` uses `asyncio.run(async_main())` to create, run, and close the event loop. |
| **Coroutines (`async def` & `await`)** | Functions that can pause execution at `await` points and resume when data is ready. | `process_single_job(job, timeout)` pauses while waiting for enrichment response. |
| **`async with` (Context Managers)** | Asynchronous setup and teardown (`__aenter__` and `__aexit__`). | Used in two key places: <br>1. `async with semaphore:` to control concurrency.<br>2. `async with asyncio.timeout(...):` to guard against hung jobs. |
| **`asyncio.Semaphore`** | Controls how many tasks may enter a critical section at once. | Ensures the batch processor **never dispatches all jobs at once**, protecting downstream databases and APIs. |
| **`asyncio.gather`** | Concurrently schedules multiple coroutines and collects all results. | `await asyncio.gather(*tasks)` launches all throttled worker coroutines concurrently. |
| **Fault Isolation & Timeouts** | A failure or timeout in one job must never crash or stall other jobs in the batch. | Timeouts (`TimeoutError`) and exceptions are caught locally, returning structured `JobResult` with `error_reason`. |

---

## 2. Architecture & Data Structures

### Models (`day8/models.py`)
- **`Priority`**: `StrEnum` with `HIGH`, `MEDIUM`, `LOW`.
- **`Job[T]`**: Generic frozen dataclass:
  - `id: str`
  - `job_type: str`
  - `priority: Priority`
  - `payload: T` (arbitrary typed payload)
  - `simulated_duration: float | None`
  - `should_fail: bool`
- **`JobResult[T]`**: Typed outcome:
  - `job_id: str`
  - `success: bool`
  - `duration_seconds: float`
  - `data: Any | None`
  - `error_reason: str | None` (`"TIMEOUT"`, `"RuntimeError"`, etc.)
- **`BatchSummary`**: Final aggregated statistics:
  - `total_jobs`: Total submitted jobs
  - `successful_count` & `failed_count`
  - `failure_breakdown`: Dictionary of count per reason (e.g. `{"TIMEOUT": 2, "RuntimeError": 1}`)
  - `total_wall_clock_time`: Actual batch duration
  - `sequential_equivalent_time`: Sum of individual job durations
  - `speedup_factor`: `sequential_equivalent_time / total_wall_clock_time`

### Batch Supervisor (`day8/processor.py`)
- **`process_single_job(job, per_job_timeout)`**:
  - Sets up `async with asyncio.timeout(per_job_timeout):`
  - Awaits simulated I/O latency.
  - Catches `TimeoutError` and maps to `error_reason="TIMEOUT"`.
  - Catches `Exception` and maps to `error_reason=type(exc).__name__`.
- **`run_batch(jobs, max_concurrency, per_job_timeout, on_job_start, on_job_done)`**:
  - Enforces `max_concurrency` using `asyncio.Semaphore`.
  - Dispatches workers via `asyncio.gather`.
  - Calculates metrics and returns `BatchSummary`.

---

## 3. How to Run

### Run the Interactive Demo
From the repository root:
```powershell
python Day8\src\day8\main.py
```

### Run Unit Tests
```powershell
python Day8\test_processor.py
```

---

## 4. Sample Run Output

```text
===========================================================================
  NIGHTLY ENRICHMENT ASYNC BATCH PROCESSOR
===========================================================================
[*] Dispatching batch of 15 jobs...
[*] Strict settings: max_concurrency=4, per_job_timeout=1.0s

  [START]   JOB-001 | Type: vip_tier_lookup                  | Priority: HIGH  
  [START]   JOB-002 | Type: realtime_fraud_check             | Priority: HIGH  
  [START]   JOB-003 | Type: kyc_status_refresh               | Priority: HIGH  
  [START]   JOB-004 | Type: active_sessions_audit            | Priority: HIGH  
  [SUCCESS] JOB-001 | Took 0.26s | Type: vip_tier_lookup
  [START]   JOB-005 | Type: credit_score_enrichment          | Priority: MEDIUM
  ...
  [FAILED]  JOB-012 | Took 1.00s | Reason: TIMEOUT
  [SUCCESS] JOB-015 | Took 0.26s | Type: merchant_category_lookup
  [FAILED]  JOB-014 | Took 0.61s | Reason: RuntimeError
  [FAILED]  JOB-013 | Took 1.00s | Reason: TIMEOUT

===========================================================================
  BATCH EXECUTION STRUCTURED SUMMARY
===========================================================================
  Configuration:
    - Max Concurrency    : 4 parallel workers
    - Per-Job Timeout    : 1.00 seconds
  -------------------------------------------------------------------------
  Job Counts:
    - Total Jobs         : 15
    - Successful Count   : 12 (80.0%)
    - Failed Count       : 3 (20.0%)
  -------------------------------------------------------------------------
  Failure Breakdown by Reason:
    - RuntimeError                : 1 job(s)
    - TIMEOUT                     : 2 job(s)
  -------------------------------------------------------------------------
  Performance & Speedup Comparison:
    - Sequential Equivalent Time :   8.73 seconds (if run one-by-one)
    - Concurrent Wall-Clock Time :   2.47 seconds (actual time taken)
    - Measured Speedup Factor    :   3.54x faster!
    - Wall-Clock Time Saved      :   6.26 seconds
===========================================================================
```
