"""Package exports for Day 6 Generic Pipeline Utilities."""

from .pipeline_utilities import (
    DEFAULT_DROP_INVALID,
    DEFAULT_PIPELINE_VERSION,
    MAX_BATCH_SIZE,
    Pipeline,
    PipelineConfig,
    RecordValidator,
    create_pipeline_config,
    filter_valid,
    run_demo,
)

__all__ = [
    "DEFAULT_PIPELINE_VERSION",
    "MAX_BATCH_SIZE",
    "DEFAULT_DROP_INVALID",
    "PipelineConfig",
    "create_pipeline_config",
    "RecordValidator",
    "filter_valid",
    "Pipeline",
    "run_demo",
]


def main() -> None:
    run_demo()
