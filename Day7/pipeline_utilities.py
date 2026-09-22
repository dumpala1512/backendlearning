"""
=============================================================================
Day 7: Pipeline Utilities with Behavioural Decorators
=============================================================================
This file enhances the Day 6 Pipeline with the 8 decorator concepts learned today:
1. First-Class Functions -> Passed into pipeline.map() and pipeline.filter()
2. Closures              -> make_amount_filter() captures threshold in its scope
3. Basic Decorator       -> Wrapping functions to add pre/post behavior
4. functools.wraps       -> Preserving __name__ and __doc__ across wrapped methods
5. Decorator with Args   -> @retry with 3-level nesting and exponential backoff
6. Class-Based Decorator -> @ttl_cache using __call__ to store cache state
7. Stacking Decorators   -> Order of execution when multiple decorators are combined
8. Practical Decorators  -> Decorating Pipeline methods directly with @timed
=============================================================================
"""

from __future__ import annotations

# -----------------------------------------------------------------------------
# STANDARD LIBRARY IMPORTS
# -----------------------------------------------------------------------------
from collections import defaultdict           # Automatically creates list values for new keys in group_by
from collections.abc import Callable, Iterator, Sequence  # Protocols for functions, iterators, and sequences
from dataclasses import dataclass              # Clean decorator to define Transaction data class
from functools import wraps                   # Preserves function metadata (__name__, __doc__)
import time                                   # Provides time.perf_counter() for timing & time.sleep() for delays

# -----------------------------------------------------------------------------
# TYPING IMPORTS
# -----------------------------------------------------------------------------
from typing import (
    Annotated,          # Attach documentation/metadata to types
    Any,                # Matches any value or function argument
    Final,              # Constant values that cannot be reassigned
    Generic,            # Parameterizes classes with TypeVars (e.g. Pipeline[T])
    Literal,            # Constrains values to exact options (e.g. "completed" | "failed")
    Protocol,           # Duck typing / structural subtyping interface
    Self,               # Represents an instance of the current class
    TypedDict,          # Type-safe dictionary schema
    TypeVar,            # Generic type placeholders (T, U, K)
    overload,           # Defines multiple signatures for one function
    runtime_checkable,  # Allows isinstance() checks on Protocols at runtime
)

T = TypeVar("T")  # Element type inside pipeline
U = TypeVar("U")  # Transformed element type after map()
K = TypeVar("K")  # Grouping key type for group_by()

Status = Literal["completed", "pending", "failed"]


@dataclass(frozen=True)
class Transaction:
    id: str
    amount: float
    currency: str
    status: Status


# =============================================================================
# 3. BASIC DECORATOR: Function wrapping another function
# =============================================================================

def simple_logger(func: Callable) -> Callable:
    """Basic decorator: logs when a function starts and finishes."""
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        print(f"    [LOG] Running '{func.__name__}'...")
        result = func(*args, **kwargs)
        print(f"    [LOG] Finished '{func.__name__}' -> returned {result}")
        return result
    return wrapper


# =============================================================================
# 4. functools.wraps & TIMING DECORATOR
# =============================================================================

def timed(func: Callable) -> Callable:
    """
    Measures and prints function execution time.
    Uses @wraps(func) to preserve the original function name and docstring.
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        print(f"    [TIMED] '{func.__name__}' executed in {elapsed:.6f}s")
        return result
    return wrapper


# =============================================================================
# 5. PARAMETERIZED DECORATOR (THREE-LEVEL NESTING PATTERN)
# =============================================================================

def retry(max_attempts: int = 3, delay: float = 0.02, fatal_errors: tuple = (ValueError,)):
    """
    Retries failing functions with exponential backoff.
    Aborts immediately on fatal errors.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            current_delay = delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except fatal_errors as err:
                    print(f"    [RETRY] Fatal error ({type(err).__name__}) in '{func.__name__}'. Aborting retries immediately!")
                    raise
                except Exception as err:
                    if attempt == max_attempts:
                        print(f"    [RETRY] Attempt {attempt}/{max_attempts} failed: {err}. No retries left!")
                        raise
                    print(f"    [RETRY] Attempt {attempt}/{max_attempts} failed: {err}. Retrying in {current_delay:.3f}s...")
                    time.sleep(current_delay)
                    current_delay *= 2
        return wrapper
    return decorator


# =============================================================================
# 6. CLASS-BASED DECORATOR (__call__ WITH STATE)
# =============================================================================

class ttl_cache:
    """
    Class-based caching decorator with Time-To-Live expiration.
    Maintains internal cache dictionary state across calls.
    """

    def __init__(self, ttl_seconds: float = 1.0) -> None:
        self.ttl_seconds = ttl_seconds
        self.cache: dict[tuple, tuple[float, Any]] = {}

    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            key = (args, tuple(sorted(kwargs.items())))
            now = time.time()
            if key in self.cache:
                timestamp, cached_val = self.cache[key]
                if now - timestamp < self.ttl_seconds:
                    print(f"    [CACHE HIT] Using cached result for '{func.__name__}'")
                    return cached_val

            print(f"    [CACHE MISS] Running '{func.__name__}' fresh...")
            result = func(*args, **kwargs)
            self.cache[key] = (now, result)
            return result
        return wrapper


# =============================================================================
# PIPELINE ENHANCED WITH BEHAVIOURAL DECORATORS
# =============================================================================

class Pipeline(Generic[T]):
    """
    Generic container wrapping items, enhanced with behavioural decorators.
    - filter, map, and group_by are decorated with @timed to measure performance.
    """

    def __init__(self, items: Sequence[T]) -> None:
        self._items = list(items)

    @timed
    def filter(self, predicate: Callable[[T], bool]) -> Self:
        """Filters items using a first-class predicate function (timed)."""
        return Pipeline([item for item in self._items if predicate(item)])

    @timed
    def map(self, transform: Callable[[T], U]) -> Pipeline[U]:
        """Transforms items using a first-class transform function (timed)."""
        return Pipeline([transform(item) for item in self._items])

    @timed
    def group_by(self, key_func: Callable[[T], K]) -> dict[K, list[T]]:
        """Groups items by key extracted by key_func (timed)."""
        grouped: dict[K, list[T]] = defaultdict(list)
        for item in self._items:
            grouped[key_func(item)].append(item)
        return dict(grouped)

    def collect(self) -> list[T]:
        """Unwraps the pipeline into a standard list[T]."""
        return list(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[T]:
        return iter(self._items)

    def __repr__(self) -> str:
        return f"Pipeline({self._items})"


# =============================================================================
# 1. FIRST-CLASS FUNCTIONS & 2. CLOSURES (USED BY PIPELINE)
# =============================================================================

def double_amount(tx: Transaction) -> Transaction:
    """First-class function passed directly into pipeline.map()."""
    return Transaction(tx.id, tx.amount * 2, tx.currency, tx.status)


def make_amount_filter(min_amount: float) -> Callable[[Transaction], bool]:
    """
    Closure: `predicate` captures and remembers `min_amount` from
    its enclosing scope, used directly by pipeline.filter().
    """
    def predicate(tx: Transaction) -> bool:
        return tx.amount >= min_amount

    return predicate


# =============================================================================
# 7. STACKING MULTIPLE DECORATORS ON PIPELINE OPERATIONS
# =============================================================================
# Execution flow:
# 1. @timed runs outermost (measures total elapsed time)
# 2. @ttl_cache checks cache (returns early on cache hit)
# 3. @retry handles retries only if cache misses and errors occur

@timed
@ttl_cache(ttl_seconds=5)
@retry(max_attempts=3, delay=0.02)
def process_pipeline(pipeline: Pipeline[Transaction]) -> int:
    """Counts completed transactions inside the pipeline."""
    return len(pipeline.filter(lambda tx: tx.status == "completed"))


# =============================================================================
# DEMO EXECUTION
# =============================================================================

def main() -> None:
    print("=" * 68)
    print("  DAY 7: PIPELINE UTILITIES WITH BEHAVIOURAL DECORATORS")
    print("=" * 68)

    # Sample pipeline transactions
    transactions = [
        Transaction("tx-01", 150.0, "USD", "completed"),
        Transaction("tx-02", -50.0, "USD", "completed"),
        Transaction("tx-03", 75.0,  "EUR", "completed"),
        Transaction("tx-04", 200.0, "USD", "failed"),
    ]
    pipeline = Pipeline(transactions)

    # 1. First-Class Functions
    print("\n[1] First-Class Functions (pipeline.map & pipeline.group_by):")
    doubled = pipeline.map(double_amount)
    print(f"    Original tx-01: {pipeline.collect()[0].amount} -> Doubled: {doubled.collect()[0].amount}")

    by_currency = pipeline.group_by(lambda tx: tx.currency)
    print(f"    pipeline.group_by(currency): { {k: len(v) for k, v in by_currency.items()} } (counts)")

    # 2. Closures & Variable Capture
    print("\n[2] Closures (pipeline.filter with make_amount_filter):")
    filter_100 = make_amount_filter(min_amount=100.0)
    filtered = pipeline.filter(filter_100)
    print(f"    Closure captured min_amount = {filter_100.__closure__[0].cell_contents}")
    print(f"    Items with amount >= 100: {len(filtered)} transactions")

    # 3. Basic Decorator
    print("\n[3] Basic Decorator (Wrapping and Logging):")
    @simple_logger
    def get_summary(p: Pipeline) -> str:
        return f"{len(p)} items"
    get_summary(pipeline)

    # 4. functools.wraps
    print("\n[4] functools.wraps (Preserving Method Metadata):")
    def bad_decorator(func: Callable) -> Callable:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)
        return wrapper

    @bad_decorator
    def without_wraps() -> None:
        """Docstring without wraps."""
        pass

    print(f"    Without @wraps -> name: '{without_wraps.__name__}', doc: {without_wraps.__doc__}")
    print(f"    With @wraps    -> name: '{Pipeline.filter.__name__}', doc: '{Pipeline.filter.__doc__}'")

    # 5. Parameterized Decorator (@retry)
    print("\n[5] Parameterized Decorator (@retry with 3-Level Nesting):")
    attempts = 0

    @retry(max_attempts=4, delay=0.02)
    def flaky_network_fetch() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 4:
            raise ConnectionError(f"Temporary network drop #{attempts}")
        return "Connected successfully on attempt 4!"

    print(f"    Result: {flaky_network_fetch()}")

    # 6. Class-Based Decorator (@ttl_cache)
    print("\n[6] Class-Based Decorator (@ttl_cache with State):")
    @ttl_cache(ttl_seconds=0.3)
    def cached_lookup(query: str) -> str:
        return f"Result for {query}"

    print("    Call 1 (Fresh run)  :", cached_lookup("USD"))
    print("    Call 2 (Cached run) :", cached_lookup("USD"))
    time.sleep(0.35)
    print("    Call 3 (Expired TTL):", cached_lookup("USD"))

    # 7 & 8. Stacking Decorators on Pipeline Processing
    print("\n[7 & 8] Stacking Multiple Decorators (@timed + @ttl_cache + @retry):")
    print("    Call 1 (Fresh run -> cache miss, timer runs):")
    process_pipeline(pipeline)

    print("\n    Call 2 (Repeat call -> cache hit, returns instantly):")
    process_pipeline(pipeline)

    print("\n" + "=" * 68)
    print("  ALL PIPELINE DECORATORS EXECUTED SUCCESSFULLY!")
    print("=" * 68)


if __name__ == "__main__":
    main()
