# Day 7: Generic Pipeline Utilities — Part 2 (Behavioural Decorators)

A production-grade decorator layer attached to the Day 6 Pipeline Utilities library, delivering cross-cutting concerns (timing, retries with exponential backoff, TTL caching, and runtime type checking) without modifying the internal code of pipeline functions.

---

## 4 Core Behavioural Decorators

| Decorator | Pattern / Type | Description & Capabilities |
|---|---|---|
| `@timed` | Basic Function Decorator | Measures and prints function execution duration. Preserves `__name__`, `__doc__`, and `__annotations__` using `@functools.wraps`. |
| `@retry(...)` | Parameterized Decorator (3-Level Nesting) | Retries failing functions with exponential backoff (`base_delay * backoff_factor ** attempt`). Immediately aborts on non-retryable fatal exceptions. |
| `@ttl_cache(...)` | Class-Based Decorator (`__call__`) | In-memory cache keyed by arguments with configurable Time-To-Live (TTL). Cache hits return in microseconds without executing the function body. |
| `@runtime_type_check` | Introspection Decorator (`inspect.signature`) | Enforces type hints at runtime. Validates all positional and keyword arguments, raising a descriptive `TypeError` on mismatch. |

---

## Key Python Decorator Concepts Explained

### 1. First-Class Functions
In Python, functions are first-class citizens. They can be:
- Passed as arguments to other functions (`def apply(func, val): return func(val)`).
- Returned as values from other functions (`def make_adder(x): return lambda y: x + y`).
- Assigned to variables, data structures, and dictionary dispatch tables.

### 2. Closures & Variable Capture
A **closure** occurs when an inner function remembers and retains access to variables from its enclosing lexical scope even after that enclosing scope has finished executing:
```python
def make_counter(start: int = 0):
    count = start
    def step():
        nonlocal count
        count += 1
        return count
    return step  # `step` holds a reference to `count` via its closure (__closure__)
```

### 3. Basic Decorator Mechanism
A decorator is syntactic sugar for a higher-order function:
```python
@my_decorator
def my_func():
    ...

# Identical to:
my_func = my_decorator(my_func)
```

### 4. Why `functools.wraps` is Essential
When a function is wrapped by an inner `wrapper`, Python by default overwrites the function's identity:
- `func.__name__` becomes `"wrapper"`
- `func.__doc__` becomes `None`
- `func.__annotations__` becomes `{}`

Using `@functools.wraps(func)` copies all metadata and attributes from `func` to `wrapper`, allowing introspection tools, debuggers, sphinx docs, and type checkers to inspect the original function transparently.

### 5. Parameterized Decorators: The Three-Level Nesting Pattern
When a decorator needs custom arguments (e.g. `@retry(max_attempts=3, base_delay=0.1)`), Python requires a decorator factory with 3 levels of nested functions:
```python
def retry(max_attempts: int, base_delay: float):  # Level 1: Receives decorator configuration
    def decorator(func: Callable):                # Level 2: Receives the target function
        @functools.wraps(func)
        def wrapper(*args, **kwargs):             # Level 3: Receives function arguments during call
            # Closure captures max_attempts, base_delay, and func
            ...
        return wrapper
    return decorator
```

### 6. Class-Based Decorators (`__call__`)
Classes can act as decorators by implementing `__call__`. This is ideal when the decorator needs to maintain state (such as cache dictionaries, hit counters, or rate limiters):
```python
class ttl_cache:
    def __init__(self, ttl_seconds: float = 60.0):
        self.ttl_seconds = ttl_seconds
        self._cache = {}

    def __call__(self, func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Accesses and mutates self._cache instance state
            ...
            return func(*args, **kwargs)
        return wrapper
```

### 7. Decorator Stacking Order
Decorators stack from the bottom up during definition, and execute from the top down (outside-in) during invocation:

```python
@timed                  # 1st to receive call; measures total elapsed time
@runtime_type_check     # 2nd to receive call; rejects bad types before anything runs
@ttl_cache(ttl_seconds) # 3rd to receive call; returns cached result if valid
@retry(max_attempts=3)  # 4th to receive call; retries transient network errors
def fetch_transaction_batch(batch_id: str, limit: int) -> Pipeline[Transaction]:
    ...
```

#### Execution Flow:
1. **Validation**: `@runtime_type_check` inspects argument types. If `limit="not_an_int"`, it raises `TypeError` immediately without cache lookups or network calls.
2. **Caching**: `@ttl_cache` checks if a cached response exists for `(batch_id, limit)`. On a hit, it returns the result immediately, bypassing `@retry` and the underlying function.
3. **Resilience**: On a cache miss, `@retry` invokes the target function. If transient errors occur, it retries with exponential backoff. If a fatal exception (`ValueError`, `KeyError`) occurs, it stops immediately.
4. **Telemetry**: `@timed` records and prints the end-to-end duration of the entire process.

---

## How to Run

### Option 1: Via UV package script (recommended)
From `Day7` or project root:
```bash
uv run day7
```

### Option 2: Via Python module runner
```bash
uv run python -m day7
```

### Option 3: Direct file execution
```bash
uv run python Day7/src/day7/pipeline_utilities.py
```

---

## Example Output

```text
===========================================================================
  DAY 7: BEHAVIOURAL DECORATORS FOR PIPELINE UTILITIES
===========================================================================

--- [1] @timed & functools.wraps Metadata Preservation ---
  [TIMED] 'sample_worker' executed in 0.010385s
    Result: 30
    Preserved Function Name : 'sample_worker'
    Preserved Docstring     : 'Add two numbers after a brief calculation pause.'
    Preserved Annotations   : {'x': <class 'int'>, 'y': <class 'int'>, 'return': <class 'int'>}

--- [2] @retry (Three-Level Nesting, Backoff & Fatal Exceptions) ---
  [RETRY] Attempt 1/3 failed for 'flaky_service': Temporary database timeout (fail #1). Retrying in 0.020s...
  [RETRY] Attempt 2/3 failed for 'flaky_service': Temporary database timeout (fail #2). Retrying in 0.040s...
    Outcome: Connected successfully on 3rd attempt!

    Testing Fatal Exception Abort (No useless retries on ValueError):
  [RETRY] Non-retryable error 'ValueError' in 'bad_data_service'. Aborting retries immediately: Corrupted record payload
    Successfully aborted without retrying: Caught Corrupted record payload

--- [3] @ttl_cache (Class-Based Decorator via __call__) ---
  [CACHE MISS] 'expensive_lookup' evaluating fresh result...
    Call 1 (Fresh computation): Result for 'query-1' (computed #1)
  [CACHE HIT] 'expensive_lookup' returned cached result (age: 0.000s)
    Call 2 (Immediate repeat -> Cache Hit): Result for 'query-1' (computed #1)
    Sleeping 0.35s to allow cache TTL expiration...
  [CACHE MISS] 'expensive_lookup' evaluating fresh result...
    Call 3 (After TTL expiration -> Fresh computation): Result for 'query-1' (computed #2)

--- [4] @runtime_type_check (Signature Type Validation) ---
    Valid Call: Configured 'tx_cleaner' (batch_size=100, strict=False)
    Invoking with invalid type (batch_size='invalid_string'):
    Caught expected TypeError: Type mismatch for parameter 'batch_size' in 'configure_pipeline': expected <class 'int'>, received str ('invalid_string')

--- [5] Stacked Decorators: @timed + @runtime_type_check + @ttl_cache + @retry ---
    Execution pipeline flow (outermost to innermost):
      1. @timed              -> measures full outer execution duration
      2. @runtime_type_check -> validates arguments first (aborts before cache/network)
      3. @ttl_cache          -> returns cached pipeline if available (skips retries & work)
      4. @retry              -> retries transient failures with backoff only on cache misses

  Case A: Type Check Violation (caught before network or cache):
    Intercepted at entry: Type mismatch for parameter 'limit' in 'fetch_transaction_batch': expected <class 'int'>, received str ('not_an_int')

  Case B: First Run with Transient Failures (Retries with backoff, then caches):
  [CACHE MISS] 'fetch_transaction_batch' evaluating fresh result...
  [RETRY] Attempt 1/3 failed for 'fetch_transaction_batch': Transient network drop (attempt 1). Retrying in 0.030s...
  [RETRY] Attempt 2/3 failed for 'fetch_transaction_batch': Transient network drop (attempt 2). Retrying in 0.060s...
  [TIMED] 'fetch_transaction_batch' executed in 0.090803s
    Retrieved: Pipeline(items=[Transaction(id='batch-retry-01', amount=250.0, currency='USD', status='completed'), Transaction(id='batch-retry-02', amount=-10.0, currency='USD', status='completed')])

  Case C: Second Run (Cache Hit - No retries, instant response):
  [CACHE HIT] 'fetch_transaction_batch' returned cached result (age: 0.091s)
  [TIMED] 'fetch_transaction_batch' executed in 0.000052s
    Retrieved: Pipeline(items=[Transaction(id='batch-retry-01', amount=250.0, currency='USD', status='completed'), Transaction(id='batch-retry-02', amount=-10.0, currency='USD', status='completed')])

  Case D: Fatal Error (Aborts retry cycle immediately):
  [CACHE MISS] 'fetch_transaction_batch' evaluating fresh result...
  [RETRY] Non-retryable error 'ValueError' in 'fetch_transaction_batch'. Aborting retries immediately: Batch 'batch-fatal' contains invalid checksum!
    Stopped immediately on fatal error: Batch 'batch-fatal' contains invalid checksum!

  Case E: Downstream Pipeline Processing with @timed & @runtime_type_check:
  [TIMED] 'transform_and_summarize' executed in 0.000039s
    Tax-adjusted summary: {'USD': 259.2}

===========================================================================
  ALL DAY 7 DECORATORS EXECUTED AND VERIFIED SUCCESSFULLY!
===========================================================================
```
