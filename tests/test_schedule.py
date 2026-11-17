import json
from datetime import datetime

import pytest

from shorts import store
from shorts.publish import upload_body
from shorts.slots import TZ, Slot

SLOT = Slot(datetime(2026, 11, 17, 20, 0, tzinfo=TZ), "Tue", "20:00")


@pytest.fixture
def meta():
    return store.load_spec("two-sum").youtube


@pytest.fixture
def published_file(tmp_path, monkeypatch):
    path = tmp_path / "published.json"
    monkeypatch.setattr(store, "PUBLISHED", path)
    return path


def test_body_has_publish_at_utc(meta):
    body = upload_body(meta, "private", SLOT.publish_at)
    assert body["status"]["publishAt"] == "2026-11-18T01:00:00Z"
    assert body["status"]["privacyStatus"] == "private"


def test_body_without_publish_at(meta):
    body = upload_body(meta, "private", None)
    assert "publishAt" not in body["status"]


def test_mark_published_records_slot(published_file):
    store.mark_published("x", "vid", SLOT)
    entry = json.loads(published_file.read_text())["x"]
    assert entry["publish_at"] == "2026-11-18T01:00:00+00:00"
    assert entry["weekday"] == "Tue"
    assert entry["window"] == "20:00"


def test_mark_published_without_slot(published_file):
    store.mark_published("x", "vid")
    assert set(json.loads(published_file.read_text())["x"]) == {"video_id", "at"}


def test_scheduled_ping_text():
    from pipeline import scheduled_message
    assert (scheduled_message("Two Sum", SLOT, "https://studio.youtube.com/video/v/edit")
            == "🎬 Two Sum goes public Tue 8pm ET (Nov 17) unless you cancel: https://studio.youtube.com/video/v/edit")
