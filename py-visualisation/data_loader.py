"""Data loading utilities for Strava dashboard."""

import polars as pl
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class StravaDataLoader:
    """Load and process Strava data from Kedro pipeline outputs."""

    def __init__(self, data_path: str = "../kedro-strava-analytics/data"):
        self.data_path = Path(data_path)
        self.activities_path = self.data_path / "01_raw" / "strava_activities.csv"
        self.streams_path = self.data_path / "02_intermediate" / "activity_streams.parquet"

    def load_activities(self) -> Optional[pl.DataFrame]:
        """Load activities data from CSV file."""
        try:
            if not self.activities_path.exists():
                logger.warning(f"Activities file not found: {self.activities_path}")
                return None

            df = pl.read_csv(self.activities_path)

            # Filter only running activities
            runs_df = df.filter(pl.col("sport_type") == "Run")

            # Convert date columns
            if "start_date" in runs_df.columns:
                runs_df = runs_df.with_columns([
                    pl.col("start_date").str.to_datetime(format="%Y-%m-%dT%H:%M:%SZ").alias("date")
                ])

            # Calculate pace in min/km
            if "distance" in runs_df.columns and "moving_time" in runs_df.columns:
                runs_df = runs_df.with_columns([
                    (pl.col("moving_time") / 60 / (pl.col("distance") / 1000))
                    .alias("pace_min_per_km")
                ])

                # Filter out unrealistic paces (slower than 15 min/km or faster than 2 min/km)
                runs_df = runs_df.filter(
                    (pl.col("pace_min_per_km") >= 2.0) &
                    (pl.col("pace_min_per_km") <= 15.0)
                )

            return runs_df

        except Exception as e:
            logger.error(f"Error loading activities: {e}")
            return None

    def get_weekly_stats(self, df: pl.DataFrame) -> dict:
        """Calculate weekly statistics."""
        if df is None or df.is_empty():
            return {
                "kms_this_week": 0,
                "kms_ytd": 0,
                "avg_pace_this_week": 0
            }

        now = datetime.now()
        # Start of the week at midnight Monday
        week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        year_start = datetime(now.year, 1, 1)

        # This week's data
        this_week = df.filter(
            pl.col("date") >= week_start
        )

        # Year to date
        ytd = df.filter(
            pl.col("date") >= year_start
        )

        kms_this_week = this_week.select(
            (pl.col("distance") / 1000).sum()
        ).item() or 0

        kms_ytd = ytd.select(
            (pl.col("distance") / 1000).sum()
        ).item() or 0

        avg_pace_this_week = this_week.select(
            pl.col("pace_min_per_km").mean()
        ).item() or 0

        return {
            "kms_this_week": round(kms_this_week, 1),
            "kms_ytd": round(kms_ytd, 1),
            "avg_pace_this_week": round(avg_pace_this_week, 2)
        }

    def get_weekly_summary(self, df: pl.DataFrame, period: str = "90d") -> pd.DataFrame:
        """Get weekly summary data for charts."""
        if df is None or df.is_empty():
            return pd.DataFrame()

        now = datetime.now()

        # Determine date range based on period
        if period == "90d":
            start_date = now - timedelta(days=90)
        elif period == "6m":
            start_date = now - timedelta(days=180)
        elif period == "ytd":
            start_date = datetime(now.year, 1, 1)
        else:  # all time
            start_date = df.select(pl.col("date").min()).item()

        # Filter data
        filtered_df = df.filter(pl.col("date") >= start_date)

        # Group by week (Monday as first day of week)
        weekly = (
            filtered_df
            .with_columns([
                pl.col("date").dt.strftime("%Y-W%W").alias("week")
            ])
            .group_by("week")
            .agg([
                (pl.col("distance") / 1000).sum().alias("total_kms"),
                pl.col("pace_min_per_km").mean().alias("avg_pace"),
                (pl.col("moving_time") / 3600).sum().alias("total_hours")
            ])
            .sort("week")
        )

        return weekly.to_pandas()

    def get_activities_list(self, df: pl.DataFrame, limit: int = 500) -> pd.DataFrame:
        """Get formatted activities list."""
        if df is None or df.is_empty():
            return pd.DataFrame()

        activities = (
            df
            .sort("date", descending=True)
            .select([
                "name",
                (pl.col("distance") / 1000).round(2).alias("distance_km"),
                (pl.col("moving_time") / 60).round(0).alias("time_minutes"),
                pl.col("pace_min_per_km").round(2).alias("pace"),
                pl.col("date").dt.strftime("%b %d, %Y").alias("date")
            ])
            .limit(limit)
        )

        return activities.to_pandas()