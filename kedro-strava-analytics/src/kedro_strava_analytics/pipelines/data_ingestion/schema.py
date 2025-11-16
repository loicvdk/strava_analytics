"""Standardized schema definitions for Strava activity data."""

import polars as pl
from typing import Dict, Any


class StravaActivitySchema:
    """Standardized schema for Strava activity data."""

    # Define the standard schema with proper data types
    SCHEMA = {
        # Core activity identifiers
        "id": pl.Int64,
        "resource_state": pl.Int64,
        "external_id": pl.String,

        # Activity metadata
        "name": pl.String,
        "type": pl.String,
        "sport_type": pl.String,
        "workout_type": pl.String,

        # Timestamps
        "start_date": pl.String,
        "start_date_local": pl.String,
        "timezone": pl.String,
        "utc_offset": pl.Float64,

        # Location information
        "location_city": pl.String,
        "location_state": pl.String,
        "location_country": pl.String,
        "start_latlng": pl.String,
        "end_latlng": pl.String,

        # Distance and time metrics
        "distance": pl.Float64,
        "moving_time": pl.Int64,
        "elapsed_time": pl.Int64,

        # Elevation
        "total_elevation_gain": pl.Float64,
        "elev_high": pl.Float64,
        "elev_low": pl.Float64,

        # Speed and pace
        "average_speed": pl.Float64,
        "max_speed": pl.Float64,

        # Power metrics
        "average_watts": pl.Float64,
        "max_watts": pl.Float64,
        "weighted_average_watts": pl.Float64,
        "device_watts": pl.Boolean,
        "kilojoules": pl.Float64,

        # Heart rate
        "has_heartrate": pl.Boolean,
        "average_heartrate": pl.Float64,
        "max_heartrate": pl.Float64,
        "heartrate_opt_out": pl.Boolean,
        "display_hide_heartrate_option": pl.Boolean,

        # Cadence
        "average_cadence": pl.Float64,

        # Temperature
        "average_temp": pl.Float64,

        # Social metrics
        "achievement_count": pl.Int64,
        "kudos_count": pl.Int64,
        "comment_count": pl.Int64,
        "athlete_count": pl.Int64,
        "photo_count": pl.Int64,
        "total_photo_count": pl.Int64,
        "pr_count": pl.Int64,

        # Activity flags
        "trainer": pl.Boolean,
        "commute": pl.Boolean,
        "manual": pl.Boolean,
        "private": pl.Boolean,
        "flagged": pl.Boolean,
        "has_kudoed": pl.Boolean,
        "from_accepted_tag": pl.Boolean,

        # Visibility and gear
        "visibility": pl.String,
        "gear_id": pl.String,

        # Upload information
        "upload_id": pl.Int64,
        "upload_id_str": pl.String,

        # Suffer score
        "suffer_score": pl.Float64,

        # Complex fields (stored as strings)
        "athlete": pl.String,
        "map": pl.String,
    }

    @classmethod
    def normalize_dataframe(cls, df: pl.DataFrame) -> pl.DataFrame:
        """Normalize a DataFrame to match the standard schema.

        Parameters
        ----------
        df : pl.DataFrame
            Input DataFrame with potentially inconsistent schema

        Returns
        -------
        pl.DataFrame
            Normalized DataFrame with standard schema
        """
        if df.is_empty():
            return pl.DataFrame(schema=cls.SCHEMA)

        # Build normalized data dictionary
        normalized_data = {}

        # Process each column in the schema
        for col_name, col_type in cls.SCHEMA.items():
            if col_name in df.columns:
                # Column exists in input data
                try:
                    if col_type == pl.String:
                        # Convert complex types to string representation
                        if df[col_name].dtype in [pl.List, pl.Struct]:
                            values = df[col_name].map_elements(
                                lambda x: str(x) if x is not None else None,
                                return_dtype=pl.String
                            )
                        else:
                            values = df[col_name].cast(pl.String)
                    elif col_type == pl.Boolean:
                        # Handle boolean conversion carefully
                        values = df[col_name].map_elements(
                            lambda x: bool(x) if x is not None else None,
                            return_dtype=pl.Boolean
                        )
                    else:
                        # Direct cast for numeric types
                        values = df[col_name].cast(col_type)

                    normalized_data[col_name] = values

                except Exception as e:
                    # If casting fails, fill with nulls
                    print(f"Warning: Failed to convert column '{col_name}' to {col_type}: {e}")
                    normalized_data[col_name] = [None] * len(df)
            else:
                # Column doesn't exist in input, add as null
                normalized_data[col_name] = [None] * len(df)

        # Create new DataFrame with normalized data
        return pl.DataFrame(normalized_data, schema=cls.SCHEMA)

    @classmethod
    def create_empty_dataframe(cls) -> pl.DataFrame:
        """Create an empty DataFrame with the standard schema.

        Returns
        -------
        pl.DataFrame
            Empty DataFrame with correct schema
        """
        return pl.DataFrame(schema=cls.SCHEMA)

    @classmethod
    def validate_dataframe(cls, df: pl.DataFrame) -> bool:
        """Validate that a DataFrame matches the expected schema.

        Parameters
        ----------
        df : pl.DataFrame
            DataFrame to validate

        Returns
        -------
        bool
            True if schema matches, False otherwise
        """
        # Check if all required columns are present
        missing_cols = set(cls.SCHEMA.keys()) - set(df.columns)
        if missing_cols:
            print(f"Missing columns: {missing_cols}")
            return False

        # Check data types
        for col_name, expected_type in cls.SCHEMA.items():
            if col_name in df.columns:
                actual_type = df[col_name].dtype
                if actual_type != expected_type:
                    print(f"Column '{col_name}' has type {actual_type}, expected {expected_type}")
                    return False

        return True

    @classmethod
    def get_column_info(cls) -> Dict[str, Any]:
        """Get information about all columns in the schema.

        Returns
        -------
        Dict[str, Any]
            Dictionary with column information
        """
        return {
            "total_columns": len(cls.SCHEMA),
            "column_types": {name: str(dtype) for name, dtype in cls.SCHEMA.items()},
            "string_columns": [name for name, dtype in cls.SCHEMA.items() if dtype == pl.String],
            "numeric_columns": [name for name, dtype in cls.SCHEMA.items()
                              if dtype in [pl.Int64, pl.Float64]],
            "boolean_columns": [name for name, dtype in cls.SCHEMA.items() if dtype == pl.Boolean],
        }