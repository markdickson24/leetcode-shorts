"""Pick when a video goes public: rotate through weekday x time-of-day cells to learn what works."""
import random
from collections import Counter
from datetime import datetime, time, timedelta
from typing import NamedTuple
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/New_York")
WINDOWS = ["07:00", "12:00", "17:00", "20:00"]
MIN_LEAD = timedelta(hours=10)  # always leave time to review before it goes public


class Slot(NamedTuple):
    publish_at: datetime  # tz-aware, TZ
    weekday: str          # "Mon".."Sun"
    window: str           # one of WINDOWS


def pick_slot(now: datetime, history: dict, rng: random.Random) -> Slot:
    """Tomorrow's least-used window for that weekday (ties random), at least MIN_LEAD from now."""
    counts = Counter((e["weekday"], e["window"]) for e in history.values()
                     if e.get("weekday") and e.get("window"))
    day = now.astimezone(TZ).date()
    while True:
        day += timedelta(days=1)
        weekday = day.strftime("%a")
        options = {w: datetime.combine(day, time.fromisoformat(w), tzinfo=TZ) for w in WINDOWS}
        options = {w: t for w, t in options.items() if t >= now + MIN_LEAD}
        if not options:
            continue
        fewest = min(counts[(weekday, w)] for w in options)
        window = rng.choice(sorted(w for w in options if counts[(weekday, w)] == fewest))
        return Slot(options[window], weekday, window)
