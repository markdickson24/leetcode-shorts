"""One-time: get a YouTube refresh token for the pipeline. Run on your Mac.

1. Google Cloud Console -> new project -> enable "YouTube Data API v3"
2. OAuth consent screen: External, add yourself as a test user
3. Credentials -> Create OAuth client ID -> "Desktop app" -> download JSON as client_secret.json
4. python scripts/youtube_auth.py client_secret.json
   (add --analytics for the separate read-only token `pipeline.py report` uses)
5. Sign in with the Google account that owns the channel.
   Put the three printed values in GitHub -> Settings -> Secrets and variables -> Actions.

While the consent screen is in "Testing", refresh tokens expire after 7 days.
Publish the app (no verification is needed for your own account) to keep it.
"""
import argparse
import json

from google_auth_oauthlib.flow import InstalledAppFlow

UPLOAD_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
ANALYTICS_SCOPES = ["https://www.googleapis.com/auth/yt-analytics.readonly",
                    "https://www.googleapis.com/auth/youtube.readonly"]

ap = argparse.ArgumentParser()
ap.add_argument("client_secret", nargs="?", default="client_secret.json")
ap.add_argument("--analytics", action="store_true",
                help="read-only token for `pipeline.py report` instead of the upload token")
a = ap.parse_args()
path = a.client_secret
scopes = ANALYTICS_SCOPES if a.analytics else UPLOAD_SCOPES
creds = InstalledAppFlow.from_client_secrets_file(path, scopes).run_local_server(port=0)
if a.analytics:
    print("\nAdd this as a GitHub Actions secret (and export it to run the report locally):\n")
    print(f"YT_ANALYTICS_REFRESH_TOKEN={creds.refresh_token}")
    raise SystemExit
info = json.load(open(path))
client = info.get("installed") or info.get("web")
print("\nAdd these as GitHub Actions secrets:\n")
print(f"YT_CLIENT_ID={client['client_id']}")
print(f"YT_CLIENT_SECRET={client['client_secret']}")
print(f"YT_REFRESH_TOKEN={creds.refresh_token}")
