import random
from datetime import date, datetime, timezone

from shorts.slots import MIN_LEAD, TZ, WINDOWS, pick_slot


def et(*args):
    return datetime(*args, tzinfo=TZ)


def used(weekday, *windows):
    return {f"{weekday}-{w}": {"video_id": "v", "weekday": weekday, "window": w} for w in windows}


def test_picks_tomorrow():
    slot = pick_slot(et(2026, 11, 16, 10, 17), {}, random.Random(0))  # a Monday
    assert slot.publish_at.date() == date(2026, 11, 17)
    assert slot.weekday == "Tue"
    assert slot.window in WINDOWS


def test_least_used_window_wins():
    slot = pick_slot(et(2026, 11, 16, 10, 17), used("Tue", "07:00", "12:00", "17:00"), random.Random(0))
    assert slot.window == "20:00"


def test_ignores_entries_without_slot():
    history = {"two-sum": {"video_id": "x", "at": "2026-11-16T22:00:55+00:00"},
               **used("Tue", "07:00", "12:00", "17:00")}
    slot = pick_slot(et(2026, 11, 16, 10, 17), history, random.Random(0))
    assert slot.window == "20:00"


def test_min_lead_respected():
    now = et(2026, 11, 16, 23, 30)
    slot = pick_slot(now, used("Tue", "12:00", "17:00", "20:00"), random.Random(0))
    assert slot.publish_at - now >= MIN_LEAD


def test_dst_spring_forward():
    slot = pick_slot(et(2027, 3, 13, 10, 0), used("Sun", "12:00", "17:00", "20:00"), random.Random(0))
    assert slot.window == "07:00"
    assert slot.publish_at.astimezone(timezone.utc).hour == 11


def test_dst_fall_back():
    slot = pick_slot(et(2026, 10, 31, 10, 0), used("Sun", "12:00", "17:00", "20:00"), random.Random(0))
    assert slot.window == "07:00"
    assert slot.publish_at.astimezone(timezone.utc).hour == 12


def test_deterministic_with_seed():
    now = et(2026, 11, 16, 10, 17)
    assert pick_slot(now, {}, random.Random(1)) == pick_slot(now, {}, random.Random(1))
