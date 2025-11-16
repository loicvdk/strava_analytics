"""Strava Streams data enrichment functionality."""

import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Set

import polars as pl
import pandas as pd

from .strava_client import StravaAPIClient


logger = logging.getLogger(__name__)


class StravaStreamsEnricher:
    """Handles enrichment of activity data with detailed streams information."""

    # All available stream types from Strava API
    AVAILABLE_STREAM_TYPES = [
        "time",
        "distance",
        "latlng",
        "altitude",
        "velocity_smooth",
        "heartrate",
        "cadence",
        "watts",
        "temp",
        "moving",
        "grade_smooth"
    ]

    def __init__(self, client: StravaAPIClient):
        """Initialize the streams enricher.

        Parameters
        ----------
        client : StravaAPIClient
            Configured Strava API client
        """
        self.client = client

    async def get_activity_streams(
        self,
        activity_id: int,
        stream_types: List[str] = None
    ) -> Dict[str, Any]:
        """Get streams data for a specific activity.

        Parameters
        ----------
        activity_id : int
            The Strava activity ID
        stream_types : List[str], optional
            List of stream types to fetch. If None, fetches all available types.

        Returns
        -------
        Dict[str, Any]
            Dictionary containing stream data organized by stream type
        """
        if stream_types is None:
            stream_types = self.AVAILABLE_STREAM_TYPES

        # Join stream types with comma for API request
        stream_types_str = ",".join(stream_types)

        endpoint = f"/activities/{activity_id}/streams"
        params = {
            "keys": stream_types_str,
            "key_by_type": "true"  # Returns data organized by stream type
        }

        try:
            logger.debug(f"Fetching streams for activity {activity_id}: {stream_types_str}")
            streams_data = await self.client._make_request(endpoint, params)

            # The API returns a list of stream objects, each with type, data, and series_type
            # We need to organize this into a more useful format
            organized_streams = {}

            # Handle case where API returns an error message instead of stream data
            if isinstance(streams_data, str):
                logger.warning(f"API returned error message for activity {activity_id}: {streams_data}")
                return {}

            if not isinstance(streams_data, list):
                # Check if it's a dict - the API sometimes returns streams as a dict
                if isinstance(streams_data, dict):
                    if "errors" in streams_data or "message" in streams_data:
                        logger.debug(f"No streams available for activity {activity_id}: {streams_data}")
                        return {}
                    else:
                        # Convert dict format to list format
                        logger.debug(f"Converting dict streams response for activity {activity_id}")
                        streams_list = []
                        for stream_type, stream_info in streams_data.items():
                            if isinstance(stream_info, dict) and "data" in stream_info:
                                streams_list.append({
                                    "type": stream_type,
                                    "data": stream_info["data"],
                                    "series_type": stream_info.get("series_type", "distance")
                                })
                        streams_data = streams_list
                else:
                    logger.warning(f"Unexpected API response format for activity {activity_id}: {type(streams_data)}")
                    return {}

            for stream in streams_data:
                if not isinstance(stream, dict):
                    logger.warning(f"Unexpected stream format: {type(stream)}")
                    continue

                stream_type = stream.get("type")
                stream_data = stream.get("data", [])
                series_type = stream.get("series_type", "distance")

                if stream_type and stream_data:
                    organized_streams[stream_type] = {
                        "data": stream_data,
                        "series_type": series_type,
                        "length": len(stream_data)
                    }

            logger.debug(f"Successfully fetched {len(organized_streams)} stream types for activity {activity_id}")
            return organized_streams

        except Exception as e:
            # Log the error but don't raise - some activities might not have streams
            logger.warning(f"Failed to fetch streams for activity {activity_id}: {e}")
            return {}

    def normalize_streams_data(
        self,
        activity_id: int,
        streams_data: Dict[str, Any]
    ) -> pl.DataFrame:
        """Normalize streams data into a structured DataFrame format.

        Parameters
        ----------
        activity_id : int
            The activity ID these streams belong to
        streams_data : Dict[str, Any]
            Raw streams data from the API

        Returns
        -------
        pl.DataFrame
            Normalized DataFrame with columns: activity_id, stream_type, time_index, value
        """
        if not streams_data:
            return pl.DataFrame(schema={
                "activity_id": pl.Int64,
                "stream_type": pl.String,
                "time_index": pl.Int64,
                "value": pl.Float64,
                "series_type": pl.String
            })

        rows = []

        for stream_type, stream_info in streams_data.items():
            data_points = stream_info.get("data", [])
            series_type = stream_info.get("series_type", "distance")

            for idx, value in enumerate(data_points):
                # Handle different data types
                if stream_type == "latlng" and isinstance(value, list) and len(value) == 2:
                    # For latlng, create two separate entries: latitude and longitude
                    rows.append({
                        "activity_id": activity_id,
                        "stream_type": "latitude",
                        "time_index": idx,
                        "value": float(value[0]),
                        "series_type": series_type
                    })
                    rows.append({
                        "activity_id": activity_id,
                        "stream_type": "longitude",
                        "time_index": idx,
                        "value": float(value[1]),
                        "series_type": series_type
                    })
                elif stream_type == "moving" and isinstance(value, bool):
                    # Convert boolean to float (1.0 for True, 0.0 for False)
                    rows.append({
                        "activity_id": activity_id,
                        "stream_type": stream_type,
                        "time_index": idx,
                        "value": float(value),
                        "series_type": series_type
                    })
                else:
                    # Handle numeric values
                    try:
                        float_value = float(value) if value is not None else None
                        rows.append({
                            "activity_id": activity_id,
                            "stream_type": stream_type,
                            "time_index": idx,
                            "value": float_value,
                            "series_type": series_type
                        })
                    except (ValueError, TypeError):
                        logger.warning(f"Could not convert value {value} to float for {stream_type}")
                        continue

        return pl.DataFrame(rows)

    async def _process_single_activity(self, activity_id: int) -> pl.DataFrame | None:
        """Process a single activity to get its streams data.

        Parameters
        ----------
        activity_id : int
            The activity ID to process

        Returns
        -------
        pl.DataFrame | None
            Normalized streams DataFrame for this activity, or None if no streams
        """
        try:
            streams_data = await self.get_activity_streams(activity_id)

            if streams_data:
                normalized_streams = self.normalize_streams_data(activity_id, streams_data)
                if not normalized_streams.is_empty():
                    return normalized_streams

            return None

        except Exception as e:
            logger.warning(f"Failed to process activity {activity_id}: {e}")
            raise  # Re-raise so gather() can catch it as an exception

    async def enrich_activities_with_streams(
        self,
        activities_df: pl.DataFrame,
        existing_streams_df: pl.DataFrame = None,
        rate_limit_delay: float = 1.0,
        max_concurrent_requests: int = 10,
        save_every_n_batches: int = 5
    ) -> pl.DataFrame:
        """Enrich ALL activities with streams data, processing all missing activities in one run.

        Parameters
        ----------
        activities_df : pl.DataFrame
            DataFrame containing activities to enrich
        existing_streams_df : pl.DataFrame, optional
            Existing streams data to avoid re-fetching
        rate_limit_delay : float
            Delay between batch requests in seconds (default: 1.0)
        max_concurrent_requests : int
            Maximum concurrent API requests per batch (default: 10)
        save_every_n_batches : int
            Save intermediate results every N batches for crash recovery (default: 5)

        Returns
        -------
        pl.DataFrame
            Combined streams DataFrame (existing + new)
        """
        if activities_df.is_empty():
            logger.info("No activities to enrich with streams")
            return existing_streams_df or pl.DataFrame()

        # Get activity IDs that need streams data
        activity_ids = set(activities_df.select("id").to_series().to_list())

        # Remove activities that already have streams data
        if existing_streams_df is not None and not existing_streams_df.is_empty():
            existing_activity_ids = set(existing_streams_df.select("activity_id").unique().to_series().to_list())
            activity_ids = activity_ids - existing_activity_ids
            logger.info(f"Found {len(existing_activity_ids)} activities with existing streams data")

        if not activity_ids:
            logger.info("All activities already have streams data")
            return existing_streams_df or pl.DataFrame()

        activity_ids_to_process = list(activity_ids)
        total_activities = len(activity_ids_to_process)

        logger.info(f"🌊 Processing streams for ALL {total_activities} activities without streams data")
        logger.info(f"📊 Estimated time: {total_activities * (rate_limit_delay + 2):.0f} seconds")

        processed_count = 0
        failed_count = 0

        # Start with existing streams data
        working_streams_df = existing_streams_df.clone() if existing_streams_df is not None and not existing_streams_df.is_empty() else pl.DataFrame()

        # Process activities in batches to respect rate limits
        batch_size = max_concurrent_requests

        for i in range(0, total_activities, batch_size):
            batch_ids = activity_ids_to_process[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_activities + batch_size - 1) // batch_size

            logger.info(f"🔄 Processing batch {batch_num}/{total_batches} ({len(batch_ids)} activities)")

            # Process batch concurrently
            batch_tasks = []
            for activity_id in batch_ids:
                batch_tasks.append(self._process_single_activity(activity_id))

            # Wait for batch to complete
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            # Process batch results and add to working dataframe
            batch_streams = []
            for activity_id, result in zip(batch_ids, batch_results):
                if isinstance(result, Exception):
                    logger.error(f"❌ Error processing activity {activity_id}: {result}")
                    failed_count += 1
                elif result is not None:
                    batch_streams.append(result)
                    logger.debug(f"✅ Processed streams for activity {activity_id}")
                else:
                    logger.debug(f"⚠️ No streams available for activity {activity_id}")

                processed_count += 1

            # Add batch results to working dataframe
            if batch_streams:
                batch_df = pl.concat(batch_streams, how="diagonal")
                if working_streams_df.is_empty():
                    working_streams_df = batch_df
                else:
                    working_streams_df = pl.concat([working_streams_df, batch_df], how="diagonal")

            # Progress update
            progress_pct = (processed_count / total_activities) * 100
            logger.info(f"📈 Progress: {processed_count}/{total_activities} ({progress_pct:.1f}%) - Failed: {failed_count}")

            # Save intermediate results every N batches
            if batch_num % save_every_n_batches == 0 or batch_num == total_batches:
                try:
                    # Convert to pandas for saving
                    working_streams_pandas = working_streams_df.to_pandas() if not working_streams_df.is_empty() else pd.DataFrame()

                    # Save to file (this will be picked up if pipeline restarts)
                    working_streams_pandas.to_parquet("data/02_intermediate/activity_streams.parquet", index=False)

                    # Create and save metadata
                    metadata_df = self.create_stream_metadata(working_streams_df)
                    metadata_pandas = metadata_df.to_pandas() if not metadata_df.is_empty() else pd.DataFrame()
                    metadata_pandas.to_csv("data/02_intermediate/stream_metadata.csv", index=False)

                    logger.info(f"💾 Intermediate save: {len(working_streams_df)} total streams records saved")
                except Exception as e:
                    logger.warning(f"Failed to save intermediate results: {e}")

            # Rate limiting between batches (except for last batch)
            if i + batch_size < total_activities and rate_limit_delay > 0:
                logger.info(f"⏱️ Rate limiting: waiting {rate_limit_delay}s before next batch...")
                await asyncio.sleep(rate_limit_delay)

        # Return the final working dataframe
        logger.info(f"✅ Streams enrichment completed!")
        logger.info(f"   - Total activities processed: {processed_count}")
        logger.info(f"   - Failed activities: {failed_count}")
        logger.info(f"   - Total streams records: {len(working_streams_df)}")

        return working_streams_df

    def create_stream_metadata(self, streams_df: pl.DataFrame) -> pl.DataFrame:
        """Create metadata about which activities have streams and when they were fetched.

        Parameters
        ----------
        streams_df : pl.DataFrame
            Streams data DataFrame

        Returns
        -------
        pl.DataFrame
            Metadata DataFrame with activity_id, stream_types, record_count, last_updated
        """
        if streams_df.is_empty():
            return pl.DataFrame(schema={
                "activity_id": pl.Int64,
                "stream_types": pl.String,
                "record_count": pl.Int64,
                "last_updated": pl.String
            })

        # Group by activity_id and summarize
        metadata = (
            streams_df
            .group_by("activity_id")
            .agg([
                pl.col("stream_type").unique().sort().str.concat(",").alias("stream_types"),
                pl.len().alias("record_count")
            ])
            .with_columns([
                pl.lit(datetime.now().isoformat()).alias("last_updated")
            ])
            .sort("activity_id")
        )

        logger.info(f"Created metadata for {len(metadata)} activities with streams")
        return metadata


def load_existing_streams_data(streams_file_path: str = None) -> pl.DataFrame:
    """Load existing streams data from file if it exists.

    Parameters
    ----------
    streams_file_path : str, optional
        Path to the streams data file

    Returns
    -------
    pl.DataFrame
        Existing streams data, or empty DataFrame if file doesn't exist
    """
    if streams_file_path is None:
        logger.info("No streams file path provided")
        return pl.DataFrame()

    try:
        path = Path(streams_file_path)
        if path.exists():
            logger.info(f"Loading existing streams data from {streams_file_path}")

            if path.suffix.lower() == '.parquet':
                df = pl.read_parquet(streams_file_path)
            else:
                # Fallback to CSV
                df = pl.read_csv(streams_file_path)

            logger.info(f"Loaded {len(df)} streams records for {df.select('activity_id').n_unique()} activities")
            return df
        else:
            logger.info(f"No existing streams file found at {streams_file_path}")
            return pl.DataFrame()
    except Exception as e:
        logger.warning(f"Failed to load existing streams data: {e}")
        return pl.DataFrame()


async def enrich_raw_data_with_streams(
    strava_credentials: dict[str, str],
    raw_activities: pl.DataFrame,
    existing_streams: pl.DataFrame = None,
    rate_limit_delay: float = 1.0,
    max_concurrent_requests: int = 10,
    save_every_n_batches: int = 5
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Main function to enrich ALL raw activity data with streams in one run.

    Parameters
    ----------
    strava_credentials : dict[str, str]
        Strava API credentials
    raw_activities : pl.DataFrame
        Raw activities data to enrich
    existing_streams : pl.DataFrame, optional
        Existing streams data to avoid re-fetching
    rate_limit_delay : float
        Delay between batch requests in seconds (default: 1.0)
    max_concurrent_requests : int
        Maximum concurrent API requests per batch (default: 10)
    save_every_n_batches : int
        Save intermediate results every N batches for crash recovery (default: 5)

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame]
        Tuple of (enriched_streams_data, streams_metadata) as pandas DataFrames
    """
    logger.info("🌊 Starting streams enrichment process...")

    try:
        # Validate credentials
        required_keys = ["client_id", "client_secret", "refresh_token"]
        missing_keys = [key for key in required_keys if key not in strava_credentials]

        if missing_keys:
            raise ValueError(f"Missing required credentials: {missing_keys}")

        # Initialize API client
        client = StravaAPIClient(
            client_id=strava_credentials["client_id"],
            client_secret=strava_credentials["client_secret"],
            refresh_token=strava_credentials["refresh_token"]
        )

        # Initialize streams enricher
        enricher = StravaStreamsEnricher(client)

        # Convert existing_streams to Polars if it's pandas
        if existing_streams is not None and isinstance(existing_streams, pd.DataFrame):
            existing_streams = pl.from_pandas(existing_streams)

        # Enrich activities with streams data
        enriched_streams_df = await enricher.enrich_activities_with_streams(
            activities_df=raw_activities,
            existing_streams_df=existing_streams,
            rate_limit_delay=rate_limit_delay,
            max_concurrent_requests=max_concurrent_requests,
            save_every_n_batches=save_every_n_batches
        )

        # Create metadata
        metadata_df = enricher.create_stream_metadata(enriched_streams_df)

        logger.info(f"✅ Streams enrichment completed!")
        logger.info(f"   - Total streams records: {len(enriched_streams_df) if not enriched_streams_df.is_empty() else 0}")
        logger.info(f"   - Activities with streams: {len(metadata_df) if not metadata_df.is_empty() else 0}")

        # Convert to pandas for Kedro compatibility
        if enriched_streams_df is not None and not enriched_streams_df.is_empty():
            streams_pandas = enriched_streams_df.to_pandas()
        else:
            streams_pandas = pd.DataFrame()

        if metadata_df is not None and not metadata_df.is_empty():
            metadata_pandas = metadata_df.to_pandas()
        else:
            metadata_pandas = pd.DataFrame()

        return streams_pandas, metadata_pandas

    except Exception as e:
        logger.error(f"Streams enrichment failed: {e}")
        raise


def enrich_raw_data_with_streams_node(
    strava_credentials: dict[str, str],
    raw_activities: pd.DataFrame,
    existing_streams: pd.DataFrame = None,
    rate_limit_delay: float = 1.0,
    max_concurrent_requests: int = 10,
    save_every_n_batches: int = 5
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Kedro node wrapper for streams enrichment.

    This function wraps the async enrichment function to make it compatible
    with Kedro's synchronous node execution model. Processes ALL activities
    without streams data in one run.

    Parameters
    ----------
    strava_credentials : dict[str, str]
        Strava API credentials
    raw_activities : pd.DataFrame
        Raw activities data to enrich
    existing_streams : pd.DataFrame, optional
        Existing streams data to avoid re-fetching
    rate_limit_delay : float
        Delay between batch requests in seconds (default: 1.0)
    max_concurrent_requests : int
        Maximum concurrent API requests per batch (default: 10)
    save_every_n_batches : int
        Save intermediate results every N batches for crash recovery (default: 5)

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame]
        Tuple of (enriched_streams_data, streams_metadata)
    """
    # Convert pandas to Polars for processing
    raw_activities_pl = pl.from_pandas(raw_activities)
    existing_streams_pl = pl.from_pandas(existing_streams) if existing_streams is not None else None

    # Run the async function
    return asyncio.run(enrich_raw_data_with_streams(
        strava_credentials=strava_credentials,
        raw_activities=raw_activities_pl,
        existing_streams=existing_streams_pl,
        rate_limit_delay=rate_limit_delay,
        max_concurrent_requests=max_concurrent_requests,
        save_every_n_batches=save_every_n_batches
    ))