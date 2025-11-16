"""OAuth2 handler for Strava API with automated browser flow."""

import asyncio
import logging
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from typing import Any

import httpx


logger = logging.getLogger(__name__)


class AuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler to capture OAuth2 callback."""

    def do_GET(self):
        """Handle GET request with authorization code."""
        # Parse the URL to extract the code
        parsed_url = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_url.query)

        if 'code' in query_params:
            # Store the code in the server instance
            self.server.auth_code = query_params['code'][0]

            # Send success response
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()

            success_html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Authorization Successful</title>
                <style>
                    body { font-family: Arial, sans-serif; text-align: center; margin-top: 50px; }
                    .success { color: #28a745; font-size: 24px; }
                    .info { color: #666; margin-top: 20px; }
                </style>
            </head>
            <body>
                <div class="success">✅ Authorization Successful!</div>
                <div class="info">You can close this tab and return to the application.</div>
                <div class="info">The pipeline will continue automatically.</div>
            </body>
            </html>
            """
            self.wfile.write(success_html.encode())

        elif 'error' in query_params:
            # Handle authorization error
            error = query_params.get('error', ['unknown'])[0]
            self.server.auth_error = error

            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()

            error_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Authorization Failed</title>
                <style>
                    body {{ font-family: Arial, sans-serif; text-align: center; margin-top: 50px; }}
                    .error {{ color: #dc3545; font-size: 24px; }}
                    .info {{ color: #666; margin-top: 20px; }}
                </style>
            </head>
            <body>
                <div class="error">❌ Authorization Failed</div>
                <div class="info">Error: {error}</div>
                <div class="info">Please try again or check your application settings.</div>
            </body>
            </html>
            """
            self.wfile.write(error_html.encode())

        # Signal that we're done
        self.server.callback_received = True

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


class StravaOAuth2Handler:
    """Handles complete OAuth2 flow for Strava API."""

    def __init__(self, client_id: str, client_secret: str):
        """Initialize OAuth2 handler.

        Parameters
        ----------
        client_id : str
            Strava application client ID
        client_secret : str
            Strava application client secret
        """
        self.client_id = str(client_id)
        self.client_secret = client_secret
        self.redirect_uri = "http://localhost:8080/exchange_token"
        self.logger = logging.getLogger(__name__)

    def _build_auth_url(self) -> str:
        """Build the OAuth2 authorization URL."""
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': self.redirect_uri,
            'approval_prompt': 'force',
            'scope': 'read,activity:read_all'  # Full scope for activity access
        }

        base_url = "https://www.strava.com/oauth/authorize"
        return f"{base_url}?{urllib.parse.urlencode(params)}"

    def _start_callback_server(self) -> HTTPServer:
        """Start local HTTP server to handle OAuth2 callback."""
        server = HTTPServer(('localhost', 8080), AuthCallbackHandler)
        server.auth_code = None
        server.auth_error = None
        server.callback_received = False

        # Start server in a separate thread
        server_thread = Thread(target=server.serve_forever, daemon=True)
        server_thread.start()

        self.logger.info("Started local callback server on http://localhost:8080")
        return server

    def _wait_for_authorization(self, server: HTTPServer, timeout: int = 300) -> str:
        """Wait for user authorization and extract code.

        Parameters
        ----------
        server : HTTPServer
            The callback server instance
        timeout : int
            Timeout in seconds (default 5 minutes)

        Returns
        -------
        str
            Authorization code

        Raises
        ------
        TimeoutError
            If user doesn't authorize within timeout
        Exception
            If authorization fails
        """
        start_time = time.time()

        self.logger.info("Waiting for user authorization...")
        self.logger.info("Please complete the authorization in your browser")

        while time.time() - start_time < timeout:
            if server.callback_received:
                if server.auth_code:
                    self.logger.info("✅ Authorization successful!")
                    return server.auth_code
                elif server.auth_error:
                    raise Exception(f"Authorization failed: {server.auth_error}")
                else:
                    raise Exception("Authorization callback received but no code found")

            time.sleep(1)

        raise TimeoutError(f"Authorization timeout after {timeout} seconds")

    async def _exchange_code_for_tokens(self, auth_code: str) -> dict[str, Any]:
        """Exchange authorization code for access and refresh tokens.

        Parameters
        ----------
        auth_code : str
            Authorization code from OAuth2 flow

        Returns
        -------
        dict[str, Any]
            Token response containing access_token, refresh_token, etc.
        """
        self.logger.info("Exchanging authorization code for tokens...")

        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': auth_code,
            'grant_type': 'authorization_code'
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://www.strava.com/oauth/token",
                data=data
            )

            if response.status_code != 200:
                error_msg = f"Token exchange failed: {response.text}"
                self.logger.error(error_msg)
                raise Exception(error_msg)

            token_data = response.json()

            # Validate response
            required_fields = ["access_token", "refresh_token", "expires_at"]
            missing_fields = [field for field in required_fields if field not in token_data]
            if missing_fields:
                raise Exception(f"Token response missing required fields: {missing_fields}")

            self.logger.info("✅ Token exchange successful!")
            return token_data

    async def get_refresh_token(self) -> str:
        """Perform complete OAuth2 flow and return refresh token.

        Returns
        -------
        str
            Refresh token for API access
        """
        self.logger.info("🚀 Starting OAuth2 authorization flow...")

        # Build authorization URL
        auth_url = self._build_auth_url()
        self.logger.info(f"Authorization URL: {auth_url}")

        # Start callback server
        server = self._start_callback_server()

        try:
            # Open browser
            self.logger.info("🌐 Opening browser for authorization...")
            webbrowser.open(auth_url)

            # Wait for authorization
            auth_code = self._wait_for_authorization(server)

            # Exchange code for tokens
            token_data = await self._exchange_code_for_tokens(auth_code)

            # Log success info
            athlete = token_data.get('athlete', {})
            if athlete:
                name = f"{athlete.get('firstname', '')} {athlete.get('lastname', '')}".strip()
                self.logger.info(f"✅ Authorized for athlete: {name}")

            return token_data['refresh_token']

        except Exception as e:
            self.logger.error(f"❌ OAuth2 flow failed: {e}")
            raise
        finally:
            # Cleanup server
            server.shutdown()
            self.logger.info("Stopped callback server")


async def perform_oauth_flow(client_id: str, client_secret: str) -> str:
    """Perform OAuth2 flow and return refresh token.

    Parameters
    ----------
    client_id : str
        Strava application client ID
    client_secret : str
        Strava application client secret

    Returns
    -------
    str
        Refresh token for API access
    """
    oauth_handler = StravaOAuth2Handler(client_id, client_secret)
    return await oauth_handler.get_refresh_token()