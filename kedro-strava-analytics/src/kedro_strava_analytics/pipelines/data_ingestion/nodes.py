"""Data ingestion nodes for Strava activities."""

import asyncio
import logging
from datetime import datetime
from pathlib import Path

import polars as pl
import pandas as pd

from .strava_client import StravaAPIClient
from .schema import StravaActivitySchema
from .streams_enrichment import (
    enrich_raw_data_with_streams_node,
    load_existing_streams_data
)


logger = logging.getLogger(__name__)


class StravaDataIngestor:
    """Handles incremental data collection from Strava API."""

    def __init__(self, client: StravaAPIClient):
        """Initialize the data ingestor.

        Parameters
        ----------
        client : StravaAPIClient
            Configured Strava API client
        """
        self.client = client

    def _normalize_activity_schema(self, df: pl.DataFrame) -> pl.DataFrame:
        """Normalize activity DataFrame schema to handle API inconsistencies.

        Parameters
        ----------
        df : pl.DataFrame
            Activity DataFrame with potentially inconsistent schema

        Returns
        -------
        pl.DataFrame
            Normalized DataFrame with consistent schema
        """
        # Convert complex objects to strings for consistency
        complex_fields = ["athlete", "map"]
        for field in complex_fields:
            if field in df.columns:
                df = df.with_columns(
                    pl.col(field).cast(pl.String)
                )

        # Convert coordinate arrays to strings (some may be Lists, others strings)
        coordinate_fields = ["start_latlng", "end_latlng"]
        for field in coordinate_fields:
            if field in df.columns:
                # Handle List types by converting to string representation
                df = df.with_columns(
                    pl.when(pl.col(field).is_null())
                    .then(None)
                    .otherwise(
                        pl.col(field).map_elements(
                            lambda x: str(x) if x is not None else None,
                            return_dtype=pl.String
                        )
                    )
                    .alias(field)
                )

        return df

    def get_oldest_saved_activity_date(self, existing_activities: pl.DataFrame) -> datetime | None:
        """Get the date of the oldest saved activity.

        Parameters
        ----------
        existing_activities : pl.DataFrame
            Existing activities dataframe (can be empty)

        Returns
        -------
        datetime | None
            Date of the oldest saved activity, or None if no activities
        """
        if existing_activities.is_empty():
            return None

        # Get the oldest start_date
        oldest_date_str = existing_activities.select(
            pl.col("start_date").min()
        ).item()

        if oldest_date_str:
            # Parse ISO format datetime string
            if isinstance(oldest_date_str, str):
                return datetime.fromisoformat(oldest_date_str.replace("Z", "+00:00"))

        return None

    async def collect_new_activities(
        self,
        existing_activities: pl.DataFrame,
        max_activities: int = 1000
    ) -> pl.DataFrame:
        """Collect new activities from Strava API.

        Parameters
        ----------
        existing_activities : pl.DataFrame
            Existing activities dataframe (can be empty)
        max_activities : int
            Maximum number of new activities to collect, by default 1000

        Returns
        -------
        pl.DataFrame
            DataFrame containing new activities
        """
        # Strategy: Always try to fetch older activities to build historical data
        oldest_saved_date = self.get_oldest_saved_activity_date(existing_activities)

        if oldest_saved_date:
            logger.info(f"Oldest saved activity date: {oldest_saved_date}")
            logger.info("Fetching activities older than existing data...")
            # Fetch activities before the oldest saved date (going backwards in time)
            new_activities_data = await self.client.get_activities(
                before=oldest_saved_date,
                max_activities=max_activities
            )
        else:
            logger.info("No existing activities found. Fetching recent activities to start dataset.")
            # When starting fresh, get recent activities
            new_activities_data = await self.client.get_activities(
                max_activities=max_activities
            )

        if not new_activities_data:
            logger.info("No new activities found")
            return pl.DataFrame()

        # Convert to DataFrame and normalize with standard schema
        df = pl.DataFrame(new_activities_data)
        df = StravaActivitySchema.normalize_dataframe(df)

        # If we have existing activities, filter out any duplicates
        if not existing_activities.is_empty():
            existing_ids = set(existing_activities.select("id").to_series().to_list())
            new_df = df.filter(~pl.col("id").is_in(existing_ids))

            logger.info(f"Found {len(df)} activities, {len(new_df)} are new")
            return new_df

        logger.info(f"Collected {len(df)} new activities")
        return df

    def merge_with_existing(
        self,
        new_activities: pl.DataFrame,
        existing_activities: pl.DataFrame
    ) -> pl.DataFrame:
        """Merge new activities with existing ones.

        Parameters
        ----------
        new_activities : pl.DataFrame
            New activities to add
        existing_activities : pl.DataFrame
            Existing activities (can be empty)

        Returns
        -------
        pl.DataFrame
            Combined activities dataframe
        """
        if existing_activities.is_empty():
            return new_activities

        if new_activities.is_empty():
            return existing_activities

        # Combine and remove any duplicates based on activity ID
        # Use diagonal concat to handle schema differences automatically
        logger.info("Combining existing and new activities with diagonal concat")
        combined = pl.concat([existing_activities, new_activities], how="diagonal")

        deduplicated = combined.unique(subset=["id"], keep="last")

        # Sort by start_date in ascending order (oldest first for easier incremental loading)
        sorted_df = deduplicated.sort("start_date", descending=False)

        logger.info(f"Merged data: {len(sorted_df)} total activities")
        return sorted_df


def load_strava_credentials() -> dict[str, str]:
    """Load Strava API credentials with automatic OAuth2 flow if needed.

    Returns
    -------
    dict[str, str]
        Strava API credentials containing client_id, client_secret, and refresh_token

    Raises
    ------
    ValueError
        If required credentials are missing
    """
    import asyncio
    import yaml
    from pathlib import Path
    from .oauth_handler import perform_oauth_flow

    # Load credentials from file
    credentials_file = Path("conf/local/credentials.yml")

    if not credentials_file.exists():
        raise FileNotFoundError("credentials.yml file not found at conf/local/credentials.yml")

    with open(credentials_file, 'r') as f:
        all_credentials = yaml.safe_load(f)

    strava_credentials = all_credentials.get("strava_api", {})

    # Check if we have basic app credentials
    basic_keys = ["client_id", "client_secret"]
    missing_basic = [key for key in basic_keys if key not in strava_credentials]

    if missing_basic:
        raise ValueError(f"Missing required app credentials in strava_api section: {missing_basic}")

    # Check if we have refresh token, if not, perform OAuth2 flow
    if "refresh_token" not in strava_credentials or not strava_credentials["refresh_token"]:
        logger.info("🔐 No refresh token found. Starting OAuth2 authorization flow...")

        try:
            # Perform OAuth2 flow
            refresh_token = asyncio.run(perform_oauth_flow(
                strava_credentials["client_id"],
                strava_credentials["client_secret"]
            ))

            # Update credentials with new refresh token
            strava_credentials["refresh_token"] = refresh_token
            all_credentials["strava_api"] = strava_credentials

            # Save updated credentials
            with open(credentials_file, 'w') as f:
                yaml.dump(all_credentials, f, default_flow_style=False)

            logger.info("✅ OAuth2 flow completed. Refresh token saved to credentials.yml")

        except Exception as e:
            logger.error(f"❌ OAuth2 flow failed: {e}")
            raise ValueError(f"Failed to obtain refresh token through OAuth2 flow: {e}")

    return strava_credentials


def collect_strava_activities(
    strava_credentials: dict[str, str],
    existing_activities: pl.DataFrame,
    max_activities: int = 1000
) -> pd.DataFrame:
    """Collect Strava activities with incremental loading.

    Parameters
    ----------
    strava_credentials : dict[str, str]
        Strava API credentials containing client_id, client_secret, and refresh_token
    existing_activities : pl.DataFrame
        Existing activities dataframe (can be empty)
    max_activities : int
        Maximum number of new activities to collect, by default 1000

    Returns
    -------
    pl.DataFrame
        DataFrame containing all activities (existing + new)

    Raises
    ------
    ValueError
        If required credentials are missing
    Exception
        If API collection fails
    """
    # Validate credentials
    required_keys = ["client_id", "client_secret", "refresh_token"]
    missing_keys = [key for key in required_keys if key not in strava_credentials]

    if missing_keys:
        raise ValueError(f"Missing required credentials: {missing_keys}")

    logger.info("Starting Strava data collection...")

    try:
        # Initialize API client
        client = StravaAPIClient(
            client_id=strava_credentials["client_id"],
            client_secret=strava_credentials["client_secret"],
            refresh_token=strava_credentials["refresh_token"]
        )

        # Initialize data ingestor
        ingestor = StravaDataIngestor(client)

        # Collect new activities
        new_activities = asyncio.run(
            ingestor.collect_new_activities(
                existing_activities=existing_activities,
                max_activities=max_activities
            )
        )

        # Merge with existing activities
        all_activities = ingestor.merge_with_existing(new_activities, existing_activities)

        logger.info(f"Data collection completed. Total activities: {len(all_activities)}")

        # Convert to pandas for saving (since catalog uses pandas.CSVDataset)
        return all_activities.to_pandas()

    except Exception as e:
        logger.error(f"Failed to collect Strava activities: {e}")
        raise


def collect_strava_activities_day0(
    strava_credentials: dict[str, str],
    max_activities: int = 1000
) -> pd.DataFrame:
    """Day 0 job: Fetch all available activities from Strava (newest to oldest).

    This job is designed for initial data setup and fetches activities starting
    from the most recent ones. It's intended to be run once to bootstrap the dataset.

    Parameters
    ----------
    strava_credentials : dict[str, str]
        Strava API credentials containing client_id, client_secret, and refresh_token
    max_activities : int
        Maximum number of activities to fetch, by default 1000

    Returns
    -------
    pd.DataFrame
        DataFrame containing all fetched activities with standardized schema

    Raises
    ------
    ValueError
        If required strava_credentials are missing
    """
    logger.info("🚀 Starting Day 0 job: Fetching all available activities")

    try:
        # Validate credentials
        required_keys = ["client_id", "client_secret", "refresh_token"]
        missing_keys = [key for key in required_keys if key not in strava_credentials]

        if missing_keys:
            raise ValueError(f"Missing required credentials: {missing_keys}")

        logger.info("Initialized Strava API client for Day 0 data collection")

        # Initialize API client
        client = StravaAPIClient(
            client_id=strava_credentials["client_id"],
            client_secret=strava_credentials["client_secret"],
            refresh_token=strava_credentials["refresh_token"]
        )

        # Initialize data ingestor
        ingestor = StravaDataIngestor(client)

        logger.info(f"Day 0: Fetching up to {max_activities} activities from newest to oldest")

        # Fetch all activities (no existing data consideration)
        new_activities_data = asyncio.run(
            client.get_activities(max_activities=max_activities)
        )

        if not new_activities_data:
            logger.info("No activities found")
            # Return empty DataFrame with correct schema
            empty_df = StravaActivitySchema.create_empty_dataframe()
            return empty_df.to_pandas()

        # Convert to DataFrame with standardized schema
        activities_df = pl.DataFrame(new_activities_data)
        activities_df = StravaActivitySchema.normalize_dataframe(activities_df)

        # Sort by date (oldest first for consistency)
        activities_df = activities_df.sort("start_date", descending=False)

        logger.info(f"Day 0 completed: Collected {len(activities_df)} activities")
        if len(activities_df) > 0:
            min_date = activities_df.select(pl.col("start_date").min()).item()
            max_date = activities_df.select(pl.col("start_date").max()).item()
            logger.info(f"Date range: {min_date} to {max_date}")

        # Convert to pandas for saving
        return activities_df.to_pandas()

    except Exception as e:
        logger.error(f"Day 0 job failed: {e}")
        raise


def collect_strava_activities_bau(
    strava_credentials: dict[str, str],
    existing_activities: pl.DataFrame,
    max_activities: int = 100
) -> pd.DataFrame:
    """BAU job: Fetch incremental activities (newest since last update).

    This job fetches only new activities that have been created since the last
    update. It looks for activities newer than the most recent one in the dataset.

    Parameters
    ----------
    strava_credentials : dict[str, str]
        Strava API credentials containing client_id, client_secret, and refresh_token
    existing_activities : pl.DataFrame
        Existing activities dataframe loaded from storage
    max_activities : int
        Maximum number of new activities to fetch, by default 100

    Returns
    -------
    pd.DataFrame
        DataFrame containing merged activities (existing + new) with standardized schema

    Raises
    ------
    ValueError
        If required strava_credentials are missing
    """
    logger.info("🔄 Starting BAU job: Fetching incremental activities")

    try:
        # Validate credentials
        required_keys = ["client_id", "client_secret", "refresh_token"]
        missing_keys = [key for key in required_keys if key not in strava_credentials]

        if missing_keys:
            raise ValueError(f"Missing required credentials: {missing_keys}")

        # Normalize existing activities to standard schema
        if not existing_activities.is_empty():
            existing_activities = StravaActivitySchema.normalize_dataframe(existing_activities)

        # Initialize API client
        client = StravaAPIClient(
            client_id=strava_credentials["client_id"],
            client_secret=strava_credentials["client_secret"],
            refresh_token=strava_credentials["refresh_token"]
        )

        # Get the date of the most recent saved activity
        latest_saved_date = None
        if not existing_activities.is_empty():
            latest_date_str = existing_activities.select(
                pl.col("start_date").max()
            ).item()

            if latest_date_str:
                if isinstance(latest_date_str, str):
                    latest_saved_date = datetime.fromisoformat(latest_date_str.replace("Z", "+00:00"))

        if latest_saved_date:
            logger.info(f"Latest saved activity date: {latest_saved_date}")
            logger.info("Fetching activities newer than existing data...")
            # Fetch activities after the latest saved date
            new_activities_data = asyncio.run(
                client.get_activities(
                    after=latest_saved_date,
                    max_activities=max_activities
                )
            )
        else:
            logger.info("No existing activities found. BAU job will fetch recent activities.")
            # If no existing data, fetch recent activities
            new_activities_data = asyncio.run(
                client.get_activities(max_activities=max_activities)
            )

        if not new_activities_data:
            logger.info("No new activities found")
            # Return existing activities as-is
            return existing_activities.to_pandas()

        # Convert new activities to DataFrame with standardized schema
        new_activities_df = pl.DataFrame(new_activities_data)
        new_activities_df = StravaActivitySchema.normalize_dataframe(new_activities_df)

        # Filter out duplicates
        if not existing_activities.is_empty():
            existing_ids = set(existing_activities.select("id").to_series().to_list())
            new_activities_df = new_activities_df.filter(~pl.col("id").is_in(existing_ids))

            if new_activities_df.is_empty():
                logger.info("All fetched activities were duplicates")
                return existing_activities.to_pandas()

        logger.info(f"Found {len(new_activities_df)} new activities")

        # Combine with existing activities
        if existing_activities.is_empty():
            combined_df = new_activities_df
        else:
            # Use diagonal concat to handle any schema differences
            combined_df = pl.concat([existing_activities, new_activities_df], how="diagonal")

        # Remove any duplicates and sort
        combined_df = combined_df.unique(subset=["id"], keep="last")
        combined_df = combined_df.sort("start_date", descending=False)

        logger.info(f"BAU completed: Total activities: {len(combined_df)}")
        logger.info(f"Added {len(new_activities_df)} new activities")

        # Convert to pandas for saving
        return combined_df.to_pandas()

    except Exception as e:
        logger.error(f"BAU job failed: {e}")
        raise


def load_existing_activities(file_path: str | None = None) -> pl.DataFrame:
    """Load existing activities from file if it exists.

    Parameters
    ----------
    file_path : str | None
        Path to the activities file, by default None

    Returns
    -------
    pl.DataFrame
        Existing activities dataframe, or empty DataFrame if file doesn't exist
    """
    if file_path is None:
        logger.info("No file path provided for existing activities")
        return pl.DataFrame()

    try:
        path = Path(file_path)
        if path.exists():
            logger.info(f"Loading existing activities from {file_path}")
            # Load as pandas first, then convert to Polars
            pandas_df = pd.read_csv(file_path)
            df = pl.from_pandas(pandas_df)

            # Normalize schema to standard format
            df = StravaActivitySchema.normalize_dataframe(df)

            return df
        else:
            logger.info(f"No existing activities file found at {file_path}")
            return pl.DataFrame()
    except Exception as e:
        logger.warning(f"Failed to load existing activities: {e}")
        return pl.DataFrame()


def save_activities(activities: pl.DataFrame, file_path: str) -> None:
    """Save activities dataframe to file.

    Parameters
    ----------
    activities : pl.DataFrame
        Activities dataframe to save
    file_path : str
        Path where to save the activities

    Raises
    ------
    Exception
        If saving fails
    """
    try:
        # Ensure directory exists
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)

        # Save as CSV for compatibility
        activities.write_csv(file_path)
        logger.info(f"Activities saved to {file_path}")

    except Exception as e:
        logger.error(f"Failed to save activities: {e}")
        raise


def load_existing_streams_node(file_path: str = None) -> pd.DataFrame:
    """Kedro node to load existing streams data.

    Parameters
    ----------
    file_path : str, optional
        Path to existing streams file

    Returns
    -------
    pd.DataFrame
        Existing streams data as pandas DataFrame
    """
    streams_df = load_existing_streams_data(file_path)
    return streams_df.to_pandas() if not streams_df.is_empty() else pd.DataFrame()


def enrich_with_streams(
    strava_credentials: dict[str, str],
    raw_activities: pd.DataFrame,
    existing_streams: pd.DataFrame = None,
    rate_limit_delay: float = 1.0,
    max_concurrent_requests: int = 10,
    save_every_n_batches: int = 5
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Enrich raw activities with streams data for ALL missing activities.

    This is a wrapper function that provides parameter flexibility for Kedro.
    Processes ALL activities without streams data in one run.

    Parameters
    ----------
    strava_credentials : dict[str, str]
        Strava API credentials
    raw_activities : pd.DataFrame
        Raw activities data
    existing_streams : pd.DataFrame, optional
        Existing streams data
    rate_limit_delay : float
        Delay between batch requests in seconds
    max_concurrent_requests : int
        Maximum concurrent API requests per batch
    save_every_n_batches : int
        Save intermediate results every N batches for crash recovery

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame]
        Tuple of (streams_data, metadata)
    """
    return enrich_raw_data_with_streams_node(
        strava_credentials=strava_credentials,
        raw_activities=raw_activities,
        existing_streams=existing_streams,
        rate_limit_delay=rate_limit_delay,
        max_concurrent_requests=max_concurrent_requests,
        save_every_n_batches=save_every_n_batches
    )