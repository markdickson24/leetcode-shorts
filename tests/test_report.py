import pytest

from shorts import report
from shorts.slots import WINDOWS


def entry(weekday, window):
    return {"video_id": f"v-{weekday}-{window}", "at": "2026-11-16T22:00:00+00:00",
            "publish_at": "2026-11-18T01:00:00+00:00", "weekday": weekday, "window": window}


def stats(views_7d):
    return {"views_48h": None, "views_7d": views_7d, "avg_view_pct": None, "subs": None}


def cell(table, weekday, window):
    """The text in the weekday row under the window column of the grid."""
    lines = [l for l in table.splitlines() if l.startswith("|")]
    header = [c.strip() for c in lines[0].strip("|").split("|")]
    row = next(l for l in lines if l.strip("| ").startswith(weekday))
    return [c.strip() for c in row.strip("|").split("|")][header.index(window)]


def test_table_groups_by_cell():
    entries = {"a": entry("Tue", "20:00"), "b": entry("Tue", "20:00"), "c": entry("Wed", "07:00")}
    table = report.build_table(entries, {"a": stats(100), "b": stats(300), "c": stats(50)})
    assert cell(table, "Tue", "20:00") == "200 (n=2)"
    assert cell(table, "Wed", "07:00") == "50 (n=1)"
    assert cell(table, "Mon", WINDOWS[0]) == "–"


def test_missing_stats_show_dash():
    table = report.build_table({"a": entry("Tue", "20:00")}, {"a": stats(None)})
    assert cell(table, "Tue", "20:00") == "–"


def test_unscheduled_entries_skipped():
    entries = {"two-sum": {"video_id": "x", "at": "2026-11-16T22:00:55+00:00"}, "a": entry("Tue", "20:00")}
    table = report.build_table(entries, {"a": stats(10)})
    assert "two-sum" not in table


def test_missing_secret_message(monkeypatch):
    monkeypatch.delenv("YT_ANALYTICS_REFRESH_TOKEN", raising=False)
    with pytest.raises(SystemExit) as e:
        report.main()
    assert "YT_ANALYTICS_REFRESH_TOKEN" in str(e.value)
    assert "scripts/youtube_auth.py --analytics" in str(e.value)
