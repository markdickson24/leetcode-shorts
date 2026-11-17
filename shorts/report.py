"""Which publish slots work? Per-video YouTube Analytics, grouped by weekday x time window."""
import os
from datetime import date, datetime, timedelta
from statistics import mean
from zoneinfo import ZoneInfo

from . import store
from .slots import TZ, WINDOWS

SCOPES = ["https://www.googleapis.com/auth/yt-analytics.readonly",
          "https://www.googleapis.com/auth/youtube.readonly"]
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
# Analytics only has whole days, in Pacific time. Ending each window N calendar days after the publish
# date gives every slot at least 48h / 7 days of data; slots differ only in the long tail, where
# Shorts views have mostly decayed.
ANALYTICS_TZ = ZoneInfo("America/Los_Angeles")
WINDOWS_DAYS = {"48h": 2, "7d": 7}
LAG_DAYS = 3  # Analytics fills in over 2-3 days; newer windows would be undercounted


def scheduled(entries: dict) -> dict:
    return {slug: e for slug, e in entries.items() if e.get("weekday") and e.get("window")}


def _publish_date(e, tz=TZ) -> date:
    return datetime.fromisoformat(e["publish_at"]).astimezone(tz).date()


def _client():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(None, refresh_token=os.environ["YT_ANALYTICS_REFRESH_TOKEN"],
                        client_id=os.environ["YT_CLIENT_ID"], client_secret=os.environ["YT_CLIENT_SECRET"],
                        token_uri="https://oauth2.googleapis.com/token", scopes=SCOPES)
    return build("youtubeAnalytics", "v2", credentials=creds, cache_discovery=False)


def fetch_stats(entries: dict, client=None, today: date | None = None) -> dict:
    """slug -> {views_48h, views_7d, avg_view_pct, subs}; None where there's no complete data yet."""
    yta = client or _client()
    today = today or datetime.now(ANALYTICS_TZ).date()
    out = {}
    for slug, e in scheduled(entries).items():
        d0 = _publish_date(e, ANALYTICS_TZ)
        s = {"views_48h": None, "views_7d": None, "avg_view_pct": None, "subs": None}
        for name, days in WINDOWS_DAYS.items():
            end = d0 + timedelta(days=days)
            if end > today - timedelta(days=LAG_DAYS):
                continue
            rows = yta.reports().query(
                ids="channel==MINE", metrics="views,averageViewPercentage,subscribersGained",
                filters=f"video=={e['video_id']}", startDate=d0.isoformat(), endDate=end.isoformat(),
            ).execute(num_retries=3).get("rows") or []
            if rows:
                views, pct, subs = rows[0]
                s[f"views_{name}"] = int(views)
                s["avg_view_pct"], s["subs"] = round(float(pct), 1), int(subs)  # latest window wins
        out[slug] = s
    return out


def _fmt(v):
    return "–" if v is None else str(v)


def build_table(entries: dict, stats: dict) -> str:
    """Grid of mean 7-day views per weekday x window, then one line per video."""
    entries = scheduled(entries)
    cells = {}
    for slug, e in entries.items():
        v = stats.get(slug, {}).get("views_7d")
        if v is not None:
            cells.setdefault((e["weekday"], e["window"]), []).append(v)

    lines = ["Mean views after 7 days, by publish slot (America/New_York):", "",
             "| " + " | ".join(["Day", *WINDOWS]) + " |",
             "|" + "|".join(["---"] * (len(WINDOWS) + 1)) + "|"]
    for day in WEEKDAYS:
        row = [f"{round(mean(cells[(day, w)]))} (n={len(cells[(day, w)])})" if (day, w) in cells else "–"
               for w in WINDOWS]
        lines.append("| " + " | ".join([day, *row]) + " |")

    lines += ["", "Per video: slug, slot, views 48h, views 7d, avg view %, subs gained"]
    for slug, e in sorted(entries.items(), key=lambda kv: kv[1]["publish_at"]):
        s = stats.get(slug, {})
        lines.append(f"  {slug}: {e['weekday']} {e['window']} ({_publish_date(e)}), "
                     + ", ".join(_fmt(s.get(k)) for k in ("views_48h", "views_7d", "avg_view_pct", "subs")))
    return "\n".join(lines)


def main():
    if not os.environ.get("YT_ANALYTICS_REFRESH_TOKEN"):
        raise SystemExit("YT_ANALYTICS_REFRESH_TOKEN is not set. Get one with "
                         "`python scripts/youtube_auth.py --analytics client_secret.json` "
                         "and export it (YT_CLIENT_ID and YT_CLIENT_SECRET are needed too).")
    entries = store.published()
    print(build_table(entries, fetch_stats(entries)))
    print("\nAnalytics lags 2-3 days, so recent videos show –.")
