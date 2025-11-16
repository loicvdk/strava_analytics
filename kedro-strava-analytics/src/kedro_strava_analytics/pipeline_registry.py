"""Project pipelines."""
from __future__ import annotations

from kedro.framework.project import find_pipelines
from kedro.pipeline import Pipeline

from kedro_strava_analytics.pipelines.data_ingestion.pipeline import (
    create_day0_pipeline,
    create_bau_pipeline,
    create_streams_enrichment_pipeline
)


def register_pipelines() -> dict[str, Pipeline]:
    """Register the project's pipelines.

    Returns:
        A mapping from pipeline names to ``Pipeline`` objects.
    """
    # Only register the modern, well-designed pipelines
    pipelines = {}

    # Add specialized pipelines
    pipelines["day0"] = create_day0_pipeline()
    pipelines["bau"] = create_bau_pipeline()
    pipelines["streams"] = create_streams_enrichment_pipeline()

    # Set BAU as default since it's the most commonly used pipeline
    pipelines["__default__"] = create_bau_pipeline()

    # Note: Legacy data_ingestion pipeline is intentionally disabled
    # Use 'day0' for initial data collection or 'bau' for incremental updates

    return pipelines
