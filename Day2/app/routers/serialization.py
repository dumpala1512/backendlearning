from typing import Any
from fastapi import APIRouter
from app.services.serialization_service import demonstrate_serialization

router = APIRouter(prefix="/serialization", tags=["Serialization"])


@router.get(
    "/demo",
    summary="Demonstrate Pydantic v2 Serialization Features",
    description=(
        "Returns examples of model_dump(), model_dump_json(), include, exclude, "
        "exclude_none, exclude_unset, and exclude_defaults."
    ),
)
def get_serialization_demonstration() -> dict[str, Any]:
    """Demonstrate all serialization features covered in Day 2."""
    return demonstrate_serialization()
