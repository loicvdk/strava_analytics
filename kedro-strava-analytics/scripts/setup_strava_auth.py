#!/usr/bin/env python3
"""
Strava OAuth2 Setup Script

This script helps you set up OAuth2 authentication for the Strava API.
Follow the Strava API documentation: https://developers.strava.com/docs/getting-started/

Prerequisites:
1. Create a Strava application at https://www.strava.com/settings/api
2. Note your Client ID and Client Secret
3. Set your Authorization Callback Domain (e.g., localhost for development)

Usage:
    python scripts/setup_strava_auth.py
"""

import sys
import urllib.parse
import webbrowser
from pathlib import Path

import httpx
import yaml


def load_credentials():
    """Load existing credentials if available."""
    credentials_file = Path("conf/local/credentials.yml")
    if not credentials_file.exists():
        return {}

    with open(credentials_file, 'r') as f:
        return yaml.safe_load(f) or {}


def save_credentials(credentials_data):
    """Save credentials to file."""
    credentials_file = Path("conf/local/credentials.yml")
    credentials_file.parent.mkdir(parents=True, exist_ok=True)

    with open(credentials_file, 'w') as f:
        yaml.dump(credentials_data, f, default_flow_style=False)


def get_authorization_url(client_id: str, redirect_uri: str = "http://localhost") -> str:
    """Generate the OAuth2 authorization URL."""
    params = {
        'client_id': client_id,
        'response_type': 'code',
        'redirect_uri': redirect_uri,
        'approval_prompt': 'force',
        'scope': 'read,activity:read_all'
    }

    base_url = "https://www.strava.com/oauth/authorize"
    return f"{base_url}?{urllib.parse.urlencode(params)}"


def exchange_code_for_token(client_id: str, client_secret: str, code: str) -> dict:
    """Exchange authorization code for access and refresh tokens."""
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'code': code,
        'grant_type': 'authorization_code'
    }

    response = httpx.post("https://www.strava.com/oauth/token", data=data)

    if response.status_code != 200:
        raise Exception(f"Token exchange failed: {response.text}")

    return response.json()


def main():
    """Main setup flow."""
    print("🚀 Strava OAuth2 Setup")
    print("=" * 50)

    # Load existing credentials
    all_credentials = load_credentials()
    strava_creds = all_credentials.get('strava_api', {})

    # Get Client ID and Secret
    client_id = input(f"Enter your Strava Client ID [{strava_creds.get('client_id', '')}]: ").strip()
    if not client_id and 'client_id' in strava_creds:
        client_id = str(strava_creds['client_id'])

    if not client_id:
        print("❌ Client ID is required")
        sys.exit(1)

    client_secret = input(f"Enter your Strava Client Secret [{strava_creds.get('client_secret', 'hidden')}]: ").strip()
    if not client_secret and 'client_secret' in strava_creds:
        client_secret = strava_creds['client_secret']

    if not client_secret:
        print("❌ Client Secret is required")
        sys.exit(1)

    # Generate authorization URL
    redirect_uri = "http://localhost"
    auth_url = get_authorization_url(client_id, redirect_uri)

    print(f"\n📋 Step 1: Authorize the application")
    print(f"Visit this URL to authorize the application:")
    print(f"{auth_url}")
    print(f"\nOpening in browser...")

    try:
        webbrowser.open(auth_url)
    except Exception:
        print("Could not open browser automatically")

    print(f"\n📋 Step 2: Get the authorization code")
    print(f"After authorizing, you'll be redirected to:")
    print(f"{redirect_uri}?state=&code=AUTHORIZATION_CODE&scope=read,activity:read_all")
    print(f"\nCopy the 'code' parameter from the URL")

    code = input("\nEnter the authorization code: ").strip()

    if not code:
        print("❌ Authorization code is required")
        sys.exit(1)

    # Exchange code for tokens
    print(f"\n🔄 Exchanging code for tokens...")

    try:
        token_data = exchange_code_for_token(client_id, client_secret, code)

        # Update credentials
        all_credentials['strava_api'] = {
            'client_id': client_id,
            'client_secret': client_secret,
            'refresh_token': token_data['refresh_token']
        }

        # Save credentials
        save_credentials(all_credentials)

        print(f"✅ Success! Credentials saved to conf/local/credentials.yml")
        print(f"\nAthlete: {token_data.get('athlete', {}).get('firstname', 'Unknown')} {token_data.get('athlete', {}).get('lastname', '')}")
        print(f"Access Token expires at: {token_data.get('expires_at', 'Unknown')}")
        print(f"\n🚀 You can now run the pipeline:")
        print(f"kedro run --pipeline=data_ingestion --params=\"max_activities=5\"")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()