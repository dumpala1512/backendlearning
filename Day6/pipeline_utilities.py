"""
=============================================================================
Day 6: Essential Python Typing Concepts
=============================================================================
This file demonstrates 8 core typing concepts in a simple, practical way:
1. Final        -> Prevent reassignment (constants)
2. Literal      -> Constrain a value to specific exact options
3. Annotated    -> Attach metadata/documentation to a type hint
4. TypedDict    -> Define expected keys & types for a regular dictionary
5. TypeVar      -> Type placeholder that preserves input-to-output types
6. Generic      -> Parameterise a class with a TypeVar (e.g. Pipeline[T])
7. Protocol     -> Duck typing (structural subtyping) with type checking
8. overload     -> Define multiple type signatures for a single function
=============================================================================
"""

from collections import defaultdict
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from typing import (
    Annotated,
    Final,
    Generic,
    Literal,
    Protocol,
    TypedDict,
    TypeVar,
    get_args,
    overload,
    runtime_checkable,
)

# =============================================================================
# 1. Final: Constant values that cannot be reassigned
# =============================================================================
MAX_BATCH_SIZE: Final[int] = 500
DEFAULT_MODE: Final[str] = "strict"


# =============================================================================
# 2. Literal: Exact fixed choices (like string-based choices)
# =============================================================================
Status = Literal["completed", "pending", "failed"]
ExecutionMode = Literal["fast", "strict"]


# =============================================================================
# 3. Annotated: Attach metadata to types without changing runtime behavior
# =============================================================================
CurrencyCode = Annotated[str, "ISO 4217 3-letter currency code (e.g. USD, EUR)"]
PositiveAmount = Annotated[float, "Must be greater than 0.0"]


# =============================================================================
# 4. TypedDict: Type-safe plain Python dictionary
# =============================================================================
class PipelineConfig(TypedDict):
    name: str
    mode: ExecutionMode
    batch_size: int


# =============================================================================
# 5. TypeVar: Generic type placeholder
# =============================================================================
T = TypeVar("T")  # Represents the item type inside a pipeline
U = TypeVar("U")  # Represents a new type after transformation (map)
K = TypeVar("K")  # Represents the grouping key type (group_by)


# =============================================================================
# 6. Generic: A class parameterized by a TypeVar
# =============================================================================
class Pipeline(Generic[T]):
    """
    A generic container wrapping a list of items of type T.
    - Pipeline[Transaction] holds transactions.
    - Pipeline[str] holds strings.
    """

    def __init__(self, items: Sequence[T]) -> None:
        self._items: list[T] = list(items)

    def filter(self, predicate: Callable[[T], bool]) -> "Pipeline[T]":
        """Filter items; output stays Pipeline[T]."""
        return Pipeline([item for item in self._items if predicate(item)])

    def filter_with_validator(self, validator: "RecordValidator[T]") -> "Pipeline[T]":
        """Filter using a duck-typed Protocol validator."""
        return Pipeline([item for item in self._items if validator.validate(item)])

    def map(self, transform: Callable[[T], U]) -> "Pipeline[U]":
        """Transforms items from type T into type U: Pipeline[T] -> Pipeline[U]."""
        return Pipeline([transform(item) for item in self._items])

    def group_by(self, key_func: Callable[[T], K]) -> dict[K, list[T]]:
        """Group items by key extracted by key_func: returns dict[K, list[T]]."""
        grouped: dict[K, list[T]] = defaultdict(list)
        for item in self._items:
            grouped[key_func(item)].append(item)
        return dict(grouped)

    def collect(self) -> list[T]:
        """Unwrap the pipeline into a plain list[T]."""
        return list(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[T]:
        return iter(self._items)

    def __repr__(self) -> str:
        return f"Pipeline(items={self._items})"


# =============================================================================
# 7. Protocol: Structural Subtyping (Duck Typing)
# =============================================================================
@runtime_checkable
class RecordValidator(Protocol[T]):
    def validate(self, record: T) -> bool:
        """Return True if record is valid, False otherwise."""
        ...


# =============================================================================
# 8. @overload: Multiple function signatures for a single implementation
# =============================================================================
@overload
def summarize_pipeline(pipeline: Pipeline[T], return_summary: Literal[True]) -> str: ...

@overload
def summarize_pipeline(pipeline: Pipeline[T], return_summary: Literal[False]) -> int: ...

def summarize_pipeline(pipeline: Pipeline[T], return_summary: bool) -> str | int:
    """Actual runtime implementation handling both overloaded cases."""
    if return_summary:
        return f"Pipeline contains {len(pipeline)} items: {pipeline.collect()}"
    return len(pipeline)


# =============================================================================
# DEMO DATA & RUNTIME EXECUTION
# =============================================================================

@dataclass
class Transaction:
    id: str
    amount: PositiveAmount
    currency: CurrencyCode
    status: Status


# Structural Protocol implementation: NO inheritance from RecordValidator!
class CompletedTransactionValidator:
    def validate(self, record: Transaction) -> bool:
        return record.amount > 0 and record.status == "completed"


def main() -> None:
    print("=" * 65)
    print("  PYTHON TYPING CONCEPTS DEMO (INDIVIDUAL OUTPUTS 1 TO 8)")
    print("=" * 65)

    # 1. Final
    print(f"\n[1] Final (Constants):")
    print(f"    MAX_BATCH_SIZE = {MAX_BATCH_SIZE} (reassignment prevented by type checkers)")

    # 2. Literal
    active_mode: ExecutionMode = "strict"
    print(f"\n[2] Literal (Constrained Values):")
    print(f"    Selected Mode = '{active_mode}' (allowed: 'fast' | 'strict')")

    # 3. Annotated
    amount_metadata = get_args(PositiveAmount)[1]
    print(f"\n[3] Annotated (Type Hint Metadata):")
    print(f"    PositiveAmount type hint carries metadata: '{amount_metadata}'")

    # #using __metadata__ dunder method
    # amount_metadata = PositiveAmount.__metadata__[0]
    # print(f"\n[3] Annotated (Type Hint Metadata):")
    # print(f"    PositiveAmount type hint carries metadata: '{amount_metadata}'")

    # 4. TypedDict
    config: PipelineConfig = {
        "name": "payment_cleaner",
        "mode": active_mode,
        "batch_size": 100,
    }
    print(f"\n[4] TypedDict (Structured Dictionary):")
    print(f"    Config Dictionary = {config}")

    # Sample items
    transactions: list[Transaction] = [
        Transaction("tx-01", 150.0, "USD", "completed"),
        Transaction("tx-02", -50.0, "USD", "completed"),  # Invalid amount
        Transaction("tx-03", 75.0,  "EUR", "completed"),
        Transaction("tx-04", 200.0, "USD", "failed"),     # Invalid status
    ]

    # 5. TypeVar
    print(f"\n[5] TypeVar (Type-Preserving Transformation):")
    pipeline: Pipeline[Transaction] = Pipeline(transactions)
    receipts: Pipeline[str] = pipeline.map(
        lambda tx: f"Receipt: [{tx.id}] {tx.amount} {tx.currency}"
    )
    print(f"    Transformed Pipeline[Transaction] (TypeVar T) -> Pipeline[str] (TypeVar U)")
    print(f"    First mapped item: '{receipts.collect()[0]}'")

    # 6. Generic
    print(f"\n[6] Generic (Type-Parameterized Container):")
    print(f"    Created Generic Container: Pipeline[Transaction] holding {len(pipeline)} items")
    by_currency = pipeline.group_by(lambda tx: tx.currency)
    print(f"    Pipeline.group_by(currency): { {k: len(v) for k, v in by_currency.items()} } (tx counts)")

    # 7. Protocol
    validator = CompletedTransactionValidator()
    print(f"\n[7] Protocol (Structural Subtyping / Duck Typing):")
    print(f"    isinstance(validator, RecordValidator) = {isinstance(validator, RecordValidator)}")
    valid_pipeline = pipeline.filter_with_validator(validator)
    print(f"    Valid records retained: {len(valid_pipeline)} of {len(pipeline)} items")

    # 8. Overload
    print(f"\n[8] @overload (Multiple Signatures for One Function):")
    summary_text: str = summarize_pipeline(valid_pipeline, return_summary=True)
    count_only: int = summarize_pipeline(valid_pipeline, return_summary=False)
    print(f"    Case A (return_summary=True)  -> returns str: '{summary_text}'")
    print(f"    Case B (return_summary=False) -> returns int: {count_only}")

    print("\n" + "=" * 65)
    print("  ALL EXECUTED SUCCESSFULLY!")
    print("=" * 65)


if __name__ == "__main__":
    main()
