# Day 6: Generic Pipeline Utilities & Python Typing Abstractions

A shared library demonstrating 8 essential Python typing concepts through generic, reusable, and type-safe abstractions for backend data pipeline operations.

---

## 8 Core Typing Concepts Demonstrated

| # | Concept | Python Tool | Purpose & Explanation |
|---|---|---|---|
| 1 | **Constants / Immutability** | `Final` | Prevents reassignment or overriding of critical values like `MAX_BATCH_SIZE`. |
| 2 | **Value Constraints** | `Literal` | Restricts a parameter or type to an exact set of allowed values (e.g. `"fast" \| "strict"`). |
| 3 | **Type Metadata** | `Annotated` | Attaches documentation and validation metadata to types (e.g. `PositiveAmount`) without changing runtime behavior. |
| 4 | **Structured Dictionaries** | `TypedDict` | Enforces exact dictionary keys and value types (`PipelineConfig`) with static verification. |
| 5 | **Type Preservation** | `TypeVar` | Type placeholders (`T`, `U`, `K`) that preserve type relationships across inputs and outputs (e.g. `Pipeline[T] -> Pipeline[U]`). |
| 6 | **Generic Containers** | `Generic[T]` | Parameterizes the container class `Pipeline[T]` with support for `.filter()`, `.map()`, and `.group_by()`. |
| 7 | **Structural Subtyping** | `Protocol[T]`, `@runtime_checkable` | Enables duck typing with static checking (`RecordValidator[T]`). Any class with `.validate()` matches without explicit inheritance. |
| 8 | **Function Overloading** | `@overload` | Declares multiple distinct return type signatures for a single function (`summarize_pipeline`), e.g. `Literal[True] -> str`, `Literal[False] -> int`. |

---

## Detailed Reference

### 1. `Final`
```python
MAX_BATCH_SIZE: Final[int] = 500
DEFAULT_MODE: Final[str] = "strict"
```
Flags any reassignment attempt as an error in static type checkers (mypy/pyright).

### 2. `Literal`
```python
Status = Literal["completed", "pending", "failed"]
ExecutionMode = Literal["fast", "strict"]
```
Guarantees values can only take one of the specified literal choices without needing the overhead of an Enum class.

### 3. `Annotated`
```python
CurrencyCode = Annotated[str, "ISO 4217 3-letter currency code (e.g. USD, EUR)"]
PositiveAmount = Annotated[float, "Must be greater than 0.0"]
```
Attaches metadata readable via `get_args(...)` or `.__metadata__` while remaining standard types at runtime.

### 4. `TypedDict`
```python
class PipelineConfig(TypedDict):
    name: str
    mode: ExecutionMode
    batch_size: int
```
Provides autocomplete and type safety for standard dictionaries without converting them to classes.

### 5 & 6. `TypeVar` and `Generic[T]`
```python
T = TypeVar("T")
U = TypeVar("U")
K = TypeVar("K")

class Pipeline(Generic[T]):
    def __init__(self, items: Sequence[T]) -> None:
        self._items: list[T] = list(items)

    def filter(self, predicate: Callable[[T], bool]) -> "Pipeline[T]": ...
    def map(self, transform: Callable[[T], U]) -> "Pipeline[U]": ...
    def group_by(self, key_func: Callable[[T], K]) -> dict[K, list[T]]: ...
```
Preserves exact item types throughout multi-stage pipeline operations.

### 7. `Protocol` & `@runtime_checkable`
```python
@runtime_checkable
class RecordValidator(Protocol[T]):
    def validate(self, record: T) -> bool: ...
```
Any class implementing `validate(self, record: T) -> bool` is automatically compatible without inheriting from `RecordValidator`. `@runtime_checkable` allows `isinstance(validator, RecordValidator)` at runtime.

### 8. `@overload`
```python
@overload
def summarize_pipeline(pipeline: Pipeline[T], return_summary: Literal[True]) -> str: ...

@overload
def summarize_pipeline(pipeline: Pipeline[T], return_summary: Literal[False]) -> int: ...

def summarize_pipeline(pipeline: Pipeline[T], return_summary: bool) -> str | int:
    if return_summary:
        return f"Pipeline contains {len(pipeline)} items: {pipeline.collect()}"
    return len(pipeline)
```
Informs type checkers that passing `return_summary=True` returns `str`, while `return_summary=False` returns `int`.

---

## How to Run

From the `Day6` directory:

```bash
uv run pipeline_utilities.py
```

Or from the root directory:

```bash
uv run Day6/pipeline_utilities.py
```
