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


class FakeAnalytics:
    """Stands in for the youtubeAnalytics client: records queries, answers from `rows_for(end_date)`."""

    def __init__(self, rows_for=lambda end: [[10, 50.0, 1]]):
        self.queries, self.rows_for = [], rows_for

    def reports(self):
        return self

    def query(self, **kw):
        self.queries.append(kw)
        rows = self.rows_for(kw["endDate"])
        return type("Req", (), {"execute": lambda _self, num_retries=0: {"rows": rows} if rows else {}})()


from datetime import date  # noqa: E402

TUE_8PM = {"a": entry("Tue", "20:00")}  # publishes 2026-11-18T01:00Z = Nov 17, 17:00 PT


def test_windows_cover_full_days_for_every_slot():
    yta = FakeAnalytics()
    report.fetch_stats(TUE_8PM, client=yta, today=date(2027, 1, 1))
    assert [(q["startDate"], q["endDate"]) for q in yta.queries] == [
        ("2026-11-17", "2026-11-19"),   # >= 48h after any slot
        ("2026-11-17", "2026-11-24"),   # >= 7 days after any slot
    ]


def test_windows_inside_analytics_lag_are_skipped():
    yta = FakeAnalytics()
    stats = report.fetch_stats(TUE_8PM, client=yta, today=date(2026, 11, 21))  # 48h window ends Nov 19
    assert yta.queries == []
    assert stats["a"]["views_48h"] is None and stats["a"]["views_7d"] is None


def test_no_rows_gives_none():
    stats = report.fetch_stats(TUE_8PM, client=FakeAnalytics(lambda end: None), today=date(2027, 1, 1))
    assert stats["a"] == {"views_48h": None, "views_7d": None, "avg_view_pct": None, "subs": None}


def test_both_windows_parsed():
    rows = {"2026-11-19": [[40, 55.5, 2]], "2026-11-24": [[90, 61.25, 5]]}
    stats = report.fetch_stats(TUE_8PM, client=FakeAnalytics(rows.get), today=date(2027, 1, 1))
    assert stats["a"] == {"views_48h": 40, "views_7d": 90, "avg_view_pct": 61.2, "subs": 5}
