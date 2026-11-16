"""One-time: get a YouTube refresh token for the pipeline. Run on your Mac.

1. Google Cloud Console -> new project -> enable "YouTube Data API v3"
2. OAuth consent screen: External, add yourself as a test user
3. Credentials -> Create OAuth client ID -> "Desktop app" -> download JSON as client_secret.json
4. python scripts/youtube_auth.py client_secret.json
5. Sign in with the Google account that owns the channel.
   Put the three printed values in GitHub -> Settings -> Secrets and variables -> Actions.

While the consent screen is in "Testing", refresh tokens expire after 7 days.
Publish the app (no verification is needed for your own account) to keep it.
"""
import json
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

path = sys.argv[1] if len(sys.argv) > 1 else "client_secret.json"
creds = InstalledAppFlow.from_client_secrets_file(path, SCOPES).run_local_server(port=0)
info = json.load(open(path))
client = info.get("installed") or info.get("web")
print("\nAdd these as GitHub Actions secrets:\n")
print(f"YT_CLIENT_ID={client['client_id']}")
print(f"YT_CLIENT_SECRET={client['client_secret']}")
print(f"YT_REFRESH_TOKEN={creds.refresh_token}")
