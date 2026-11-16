"""YouTube upload and a 'ready for review' ping."""
import json
import os
import urllib.request

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def upload(path, meta, privacy="private") -> str:
    """Upload as private by default: you review in YouTube Studio, then publish."""
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    creds = Credentials(None, refresh_token=os.environ["YT_REFRESH_TOKEN"],
                        client_id=os.environ["YT_CLIENT_ID"], client_secret=os.environ["YT_CLIENT_SECRET"],
                        token_uri="https://oauth2.googleapis.com/token", scopes=SCOPES)
    yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
    body = {
        "snippet": {"title": meta.title[:100], "description": meta.description,
                    "tags": meta.tags, "categoryId": "27"},  # 27 = Education
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
    }
    req = yt.videos().insert(part="snippet,status", body=body,
                             media_body=MediaFileUpload(str(path), mimetype="video/mp4", resumable=True))
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    return resp["id"]


def notify(text, **extra):
    """POST to NOTIFY_WEBHOOK_URL if set (an n8n webhook, or a Discord/Slack incoming webhook)."""
    url = os.environ.get("NOTIFY_WEBHOOK_URL")
    if not url:
        return
    payload = {"text": text, "content": text, **extra}  # 'content' is what Discord reads
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=15)
    except Exception as e:  # a failed ping shouldn't fail the run
        print(f"notify failed: {e}")
