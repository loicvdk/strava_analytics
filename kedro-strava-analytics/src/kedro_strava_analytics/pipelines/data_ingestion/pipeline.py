"""Strava data ingestion pipeline."""

from kedro.pipeline import Pipeline, node, pipeline

from .nodes import (
    collect_strava_activities,
    load_existing_activities,
    load_strava_credentials,
    collect_strava_activities_day0,
    collect_strava_activities_bau,
    load_existing_streams_node,
    enrich_with_streams
)


def create_pipeline(**kwargs) -> Pipeline:
    """Create the data ingestion pipeline.

    Returns
    -------
    Pipeline
        A Kedro pipeline for collecting Strava activities (legacy - use specific pipelines)
    """
    return pipeline(
        [
            node(
                func=load_existing_activities,
                inputs="params:existing_activities_filepath",
                outputs="existing_activities",
                name="load_existing_activities_node",
                tags=["data_ingestion", "load_existing"],
            ),
            node(
                func=load_strava_credentials,
                inputs=None,
                outputs="strava_credentials",
                name="load_strava_credentials_node",
                tags=["data_ingestion", "credentials"],
            ),
            node(
                func=collect_strava_activities,
                inputs=[
                    "strava_credentials",
                    "existing_activities",
                    "params:max_activities",
                ],
                outputs="raw_activities",
                name="collect_strava_activities_node",
                tags=["data_ingestion", "strava_api"],
            ),
        ],
        namespace="data_ingestion",
        outputs="raw_activities",
        parameters=["max_activities", "existing_activities_filepath"],
    )


def create_day0_pipeline(**kwargs) -> Pipeline:
    """Create the Day 0 pipeline for initial data collection.

    This pipeline fetches all available activities from newest to oldest.
    Intended for first-time setup to bootstrap the dataset.

    Returns
    -------
    Pipeline
        A Kedro pipeline for Day 0 data collection
    """
    return pipeline(
        [
            node(
                func=load_strava_credentials,
                inputs=None,
                outputs="strava_credentials",
                name="load_strava_credentials_node",
                tags=["day0", "credentials"],
            ),
            node(
                func=collect_strava_activities_day0,
                inputs=[
                    "strava_credentials",
                    "params:max_activities",
                ],
                outputs="raw_activities",
                name="collect_strava_activities_day0_node",
                tags=["day0", "strava_api", "initial_load"],
            ),
        ],
        namespace="day0",
        outputs="raw_activities",
        parameters=["max_activities"],
    )


def create_bau_pipeline(**kwargs) -> Pipeline:
    """Create the BAU (Business As Usual) pipeline for incremental updates.

    This pipeline fetches only new activities since the last update.
    Intended for regular scheduled runs to keep data up-to-date.

    Returns
    -------
    Pipeline
        A Kedro pipeline for BAU incremental data collection
    """
    return pipeline(
        [
            node(
                func=load_existing_activities,
                inputs="params:existing_activities_filepath",
                outputs="existing_activities",
                name="load_existing_activities_node",
                tags=["bau", "load_existing"],
            ),
            node(
                func=load_strava_credentials,
                inputs=None,
                outputs="strava_credentials",
                name="load_strava_credentials_node",
                tags=["bau", "credentials"],
            ),
            node(
                func=collect_strava_activities_bau,
                inputs=[
                    "strava_credentials",
                    "existing_activities",
                    "params:max_activities",
                ],
                outputs="raw_activities",
                name="collect_strava_activities_bau_node",
                tags=["bau", "strava_api", "incremental"],
            ),
        ],
        namespace="bau",
        outputs="raw_activities",
        parameters=["max_activities", "existing_activities_filepath"],
    )


def create_streams_enrichment_pipeline(**kwargs) -> Pipeline:
    """Create the streams enrichment pipeline.

    This pipeline enriches existing activity data with detailed streams information
    (time-series data like heartrate, GPS coordinates, power, etc.).

    Returns
    -------
    Pipeline
        A Kedro pipeline for streams data enrichment
    """
    return pipeline(
        [
            node(
                func=load_existing_streams_node,
                inputs="params:existing_streams_filepath",
                outputs="existing_streams_data",
                name="load_existing_streams_node",
                tags=["streams", "load_existing"],
            ),
            node(
                func=load_strava_credentials,
                inputs=None,
                outputs="strava_credentials",
                name="load_strava_credentials_node",
                tags=["streams", "credentials"],
            ),
            node(
                func=enrich_with_streams,
                inputs=[
                    "strava_credentials",
                    "raw_activities",
                    "existing_streams_data",
                    "params:streams_enrichment.rate_limit_delay",
                    "params:streams_enrichment.max_concurrent_requests",
                    "params:streams_enrichment.save_every_n_batches",
                ],
                outputs=["activity_streams", "stream_metadata"],
                name="enrich_with_streams_node",
                tags=["streams", "enrichment", "strava_api"],
            ),
        ],
        namespace="streams",
        inputs=["raw_activities"],
        outputs=["activity_streams", "stream_metadata"],
        parameters=[
            "existing_streams_filepath",
            "streams_enrichment.rate_limit_delay",
            "streams_enrichment.max_concurrent_requests",
            "streams_enrichment.save_every_n_batches",
        ],
    )