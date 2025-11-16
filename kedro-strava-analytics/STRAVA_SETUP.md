# Strava API OAuth2 Setup Guide

This guide walks you through setting up OAuth2 authentication for the Strava API.

## Prerequisites

1. **Create a Strava Application**
   - Go to https://www.strava.com/settings/api
   - Click "Create App"
   - Fill in the application details:
     - **Application Name**: Your app name (e.g., "My Strava Analytics")
     - **Category**: Choose appropriate category
     - **Website**: Your website URL (can be GitHub repo)
     - **Authorization Callback Domain**: Use `localhost` for development
   - Click "Create"

2. **Note Your Credentials**
   After creating the app, you'll see:
   - **Client ID**: A numeric ID (e.g., 132395)
   - **Client Secret**: A long string (keep this secret!)

## Setup Options

### Option 1: Automated Setup (Recommended)

Use our setup script for guided OAuth2 setup:

```bash
python scripts/setup_strava_auth.py
```

This script will:
1. Ask for your Client ID and Client Secret
2. Open your browser to authorize the app
3. Help you extract the authorization code
4. Exchange it for tokens automatically
5. Save credentials to `conf/local/credentials.yml`

### Option 2: Manual Setup

#### Step 1: Get Authorization Code

1. Replace `YOUR_CLIENT_ID` in this URL with your actual Client ID:
   ```
   https://www.strava.com/oauth/authorize?client_id=YOUR_CLIENT_ID&response_type=code&redirect_uri=http://localhost&approval_prompt=force&scope=read,activity:read_all
   ```

2. Visit the URL in your browser
3. Click "Authorize" to grant permissions
4. You'll be redirected to `http://localhost?state=&code=AUTHORIZATION_CODE&scope=read,activity:read_all`
5. Copy the `code` parameter from the URL

#### Step 2: Exchange Code for Tokens

Use curl or a tool like Postman to exchange the authorization code:

```bash
curl -X POST https://www.strava.com/oauth/token \
  -d client_id=YOUR_CLIENT_ID \
  -d client_secret=YOUR_CLIENT_SECRET \
  -d code=AUTHORIZATION_CODE \
  -d grant_type=authorization_code
```

#### Step 3: Save Credentials

Create/update `conf/local/credentials.yml`:

```yaml
strava_api:
  client_id: YOUR_CLIENT_ID
  client_secret: YOUR_CLIENT_SECRET
  refresh_token: YOUR_REFRESH_TOKEN
```

## Scopes

The application requests these scopes:
- `read`: Read public profile information
- `activity:read_all`: Read all activity data including private activities

## Security Notes

1. **Keep credentials secure**: Never commit `conf/local/credentials.yml` to version control
2. **Refresh tokens**: The application automatically refreshes access tokens as needed
3. **Rate limits**: The client respects Strava's rate limits (100 requests per 15 minutes)

## Testing Your Setup

After setup, test with a small number of activities:

```bash
kedro run --pipeline=data_ingestion --params="max_activities=5"
```

For production use:

```bash
kedro run --pipeline=data_ingestion --params="max_activities=1000"
```

## Troubleshooting

### "Authorization Error"
- Double-check your Client ID and Client Secret
- Ensure the authorization callback domain matches your setup
- Make sure you authorized the correct scopes

### "Invalid refresh token"
- Re-run the OAuth2 flow to get a new refresh token
- Check that your application is still active in Strava settings

### "Rate limit exceeded"
- The client automatically handles rate limits with progress bars
- Strava allows 100 requests per 15 minutes and 1,000 per day

## API Documentation

- [Strava API Getting Started](https://developers.strava.com/docs/getting-started/)
- [OAuth2 Flow Details](https://developers.strava.com/docs/authentication/)
- [API Reference](https://developers.strava.com/docs/reference/)