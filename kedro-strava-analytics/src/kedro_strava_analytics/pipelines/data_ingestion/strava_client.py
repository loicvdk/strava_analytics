"""Strava API client with rate limiting and authentication."""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any

import httpx
import polars as pl


logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter for Strava API respecting the 100 requests per 15 minutes limit."""

    def __init__(self, max_requests: int = 95, time_window: int = 900):  # 15 minutes = 900 seconds
        """Initialize rate limiter.

        Parameters
        ----------
        max_requests : int
            Maximum requests allowed in time window (default 95 to stay safe)
        time_window : int
            Time window in seconds (default 900 = 15 minutes)
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []

    def wait_if_needed(self) -> None:
        """Wait if we're approaching rate limits."""
        now = time.time()

        # Remove old requests outside the time window
        self.requests = [req_time for req_time in self.requests if now - req_time < self.time_window]

        if len(self.requests) >= self.max_requests:
            # Calculate how long to wait
            oldest_request = min(self.requests)
            wait_time = self.time_window - (now - oldest_request) + 1  # +1 for safety

            if wait_time > 0:
                logger.info(f"Rate limit reached. Waiting {wait_time:.1f} seconds...")
                self._show_progress_bar(wait_time)

        # Record this request
        self.requests.append(now)

    def _show_progress_bar(self, duration: float) -> None:
        """Show an interactive progress bar while waiting."""
        import sys

        steps = int(duration)
        for i in range(steps):
            remaining = steps - i
            progress = i / steps
            bar_length = 30
            filled_length = int(bar_length * progress)
            bar = '█' * filled_length + '░' * (bar_length - filled_length)

            sys.stdout.write(f'\r⏳ Rate limit cooldown: [{bar}] {remaining}s remaining')
            sys.stdout.flush()
            time.sleep(1)

        # Final progress update
        sys.stdout.write(f'\r✅ Rate limit cooldown: [{"█" * bar_length}] Ready!     \n')
        sys.stdout.flush()


class StravaAPIClient:
    """Production-grade Strava API client with rate limiting and error handling."""

    BASE_URL = "https://www.strava.com/api/v3"

    def __init__(self, client_id: str, client_secret: str, refresh_token: str):
        """Initialize Strava API client.

        Parameters
        ----------
        client_id : str
            Strava application client ID
        client_secret : str
            Strava application client secret
        refresh_token : str
            User's refresh token for OAuth2
        """
        # Validate inputs
        if not all([client_id, client_secret, refresh_token]):
            raise ValueError("client_id, client_secret, and refresh_token are all required")

        self.client_id = str(client_id)  # Ensure string format
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.access_token = None
        self.token_expires_at = None
        self.rate_limiter = RateLimiter()
        self.logger = logging.getLogger(__name__)

        self.logger.info(f"Initialized Strava API client for app ID: {self.client_id}")

    async def _ensure_valid_token(self) -> None:
        """Ensure we have a valid access token."""
        if (
            self.access_token is None
            or self.token_expires_at is None
            or time.time() >= self.token_expires_at
        ):
            await self._refresh_access_token()

    async def _refresh_access_token(self) -> None:
        """Refresh the access token using the refresh token."""
        self.logger.info("Refreshing access token...")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://www.strava.com/oauth/token",
                data={
                    "client_id": str(self.client_id),  # Ensure string format
                    "client_secret": self.client_secret,
                    "refresh_token": self.refresh_token,
                    "grant_type": "refresh_token",
                }
            )

            if response.status_code != 200:
                error_msg = f"Failed to refresh token: {response.text}"
                self.logger.error(error_msg)
                raise Exception(error_msg)

            token_data = response.json()

            # Validate response contains required fields
            required_fields = ["access_token", "expires_at"]
            missing_fields = [field for field in required_fields if field not in token_data]
            if missing_fields:
                raise Exception(f"Token response missing required fields: {missing_fields}")

            self.access_token = token_data["access_token"]
            self.token_expires_at = token_data["expires_at"]

            # Update refresh token if provided (optional)
            if "refresh_token" in token_data:
                self.refresh_token = token_data["refresh_token"]

            self.logger.info("Access token refreshed successfully")

    async def _make_request(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make an authenticated request to the Strava API.

        Parameters
        ----------
        endpoint : str
            API endpoint (e.g., "/athlete/activities")
        params : dict[str, Any] | None
            Query parameters

        Returns
        -------
        dict[str, Any]
            JSON response from API
        """
        await self._ensure_valid_token()
        self.rate_limiter.wait_if_needed()

        url = f"{self.BASE_URL}{endpoint}"
        headers = {"Authorization": f"Bearer {self.access_token}"}

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params or {})

            if response.status_code == 429:  # Rate limited
                self.logger.warning("Rate limited by Strava API")
                await asyncio.sleep(60)  # Wait 1 minute
                return await self._make_request(endpoint, params)

            if response.status_code == 401:  # Unauthorized
                self.logger.error("Unauthorized - token may be invalid or expired")
                raise Exception(f"Unauthorized API request: {response.text}")

            if response.status_code != 200:
                error_msg = f"API request failed: {response.status_code} - {response.text}"
                self.logger.error(error_msg)
                raise Exception(error_msg)

            return response.json()

    async def get_activities(
        self,
        after: datetime | None = None,
        before: datetime | None = None,
        per_page: int = 30,
        max_activities: int = 1000
    ) -> list[dict[str, Any]]:
        """Fetch activities with pagination and rate limiting.

        Parameters
        ----------
        after : datetime | None
            Fetch activities after this date
        before : datetime | None
            Fetch activities before this date
        per_page : int
            Number of activities per page (max 200)
        max_activities : int
            Maximum number of activities to fetch

        Returns
        -------
        list[dict[str, Any]]
            List of activity dictionaries
        """
        all_activities = []
        page = 1

        params = {"per_page": min(per_page, 200)}  # Strava max is 200

        if after:
            params["after"] = int(after.timestamp())
        if before:
            params["before"] = int(before.timestamp())

        self.logger.info(f"Starting to fetch activities (max: {max_activities})...")

        while len(all_activities) < max_activities:
            params["page"] = page

            self.logger.info(f"Fetching page {page} (activities collected: {len(all_activities)})...")

            try:
                activities = await self._make_request("/athlete/activities", params)

                if not activities:  # No more activities
                    self.logger.info("No more activities to fetch")
                    break

                all_activities.extend(activities)

                # Check if we've reached our limit
                if len(all_activities) >= max_activities:
                    all_activities = all_activities[:max_activities]
                    self.logger.info(f"Reached maximum activities limit: {max_activities}")
                    break

                page += 1

            except Exception as e:
                self.logger.error(f"Error fetching activities page {page}: {e}")
                raise

        self.logger.info(f"Successfully fetched {len(all_activities)} activities")
        return all_activities

    async def get_latest_activity_date(self, activities: list[dict[str, Any]]) -> datetime | None:
        """Get the date of the most recent activity.

        Parameters
        ----------
        activities : list[dict[str, Any]]
            List of activities

        Returns
        -------
        datetime | None
            Date of the most recent activity, or None if no activities
        """
        if not activities:
            return None

        # Activities are returned in reverse chronological order by default
        latest_activity = activities[0]
        start_date_str = latest_activity.get("start_date")

        if start_date_str:
            # Parse ISO format: "2024-01-15T08:30:00Z"
            return datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))

        return None