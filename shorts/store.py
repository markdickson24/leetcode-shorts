"""Files on disk: the problem queue, saved specs and what's been published."""
import json
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .spec import Spec
from .templates import TEMPLATES

ROOT = Path(__file__).resolve().parent.parent
SPECS = ROOT / "specs"
QUEUE = ROOT / "problems.yaml"
PUBLISHED = ROOT / "published.json"


class _Dumper(yaml.SafeDumper):
    pass


# Multi-line strings (code, captions) as readable | blocks instead of "\n" soup.
_Dumper.add_representer(str, lambda d, s: d.represent_scalar(
    "tag:yaml.org,2002:str", s, style="|" if "\n" in s else None))


def spec_path(slug):
    return SPECS / f"{slug}.yaml"


def load_spec(slug) -> Spec:
    return Spec.model_validate(yaml.safe_load(spec_path(slug).read_text()))


def save_spec(spec: Spec):
    SPECS.mkdir(exist_ok=True)
    spec_path(spec.slug).write_text(
        yaml.dump(spec.model_dump(mode="json"), Dumper=_Dumper, sort_keys=False, allow_unicode=True, width=110))


def queue():
    return yaml.safe_load(QUEUE.read_text())


def published():
    return json.loads(PUBLISHED.read_text()) if PUBLISHED.exists() else {}


def mark_published(slug, video_id, slot=None):
    data = published()
    data[slug] = {"video_id": video_id, "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    if slot is not None:
        data[slug].update(publish_at=slot.publish_at.astimezone(timezone.utc).isoformat(timespec="seconds"),
                          weekday=slot.weekday, window=slot.window)
    PUBLISHED.write_text(json.dumps(data, indent=2) + "\n")


def next_problem():
    """First problem in the queue that isn't published and whose templates all exist."""
    done = published()
    for p in queue():
        if p["slug"] in done:
            continue
        missing = [t for t in p.get("templates", []) if t not in TEMPLATES]
        if missing:
            print(f"skip {p['slug']}: needs templates {missing}")
            continue
        return p
    return None


def problem(slug):
    for p in queue():
        if p["slug"] == slug:
            return p
    raise SystemExit(f"{slug!r} isn't in problems.yaml")
