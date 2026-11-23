"""LeetCode Shorts pipeline.

  python pipeline.py next [--upload]           next problem in the queue, end to end
  python pipeline.py run <slug> [--upload]     one problem, end to end
  python pipeline.py generate <slug>           (re)write specs/<slug>.yaml with Claude (needs USE_CLAUDE_API=1)
  python pipeline.py verify <slug>             test the spec's code and traces
  python pipeline.py render <slug> [--preview] render without uploading
  python pipeline.py report                    views per publish slot (YouTube Analytics)

End to end = saved spec (hand-written; Claude API generation only with USE_CLAUDE_API=1) -> verify -> render
-> upload as PRIVATE with a scheduled publish slot (shorts/slots.py) -> ping you.
It goes public at that slot unless you cancel it in Studio; --no-schedule keeps it private.
"""
import argparse
import os
import sys

from shorts import store
from shorts.verify import VerificationError, verify

MAX_ATTEMPTS = 3


def ensure_spec(problem, regenerate=False):
    """Load a saved spec. Generating one with the Claude API is opt-in (USE_CLAUDE_API=1):
    by default specs are written by hand (e.g. in Claude Code) and committed ahead of time."""
    path = store.spec_path(problem["slug"])
    if path.exists() and not regenerate:
        spec = store.load_spec(problem["slug"])
        return spec, verify(spec)
    if os.environ.get("USE_CLAUDE_API") != "1":
        raise SystemExit(f"no spec for {problem['slug']}: write specs/{problem['slug']}.yaml and commit it "
                         "(or set USE_CLAUDE_API=1 to generate one with the Claude API)")

    from shorts.generate import generate
    feedback = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"generating spec for {problem['slug']} (attempt {attempt})")
        try:
            spec = generate(problem, feedback)
            traces = verify(spec)
        except VerificationError as e:
            feedback = str(e)
            print(f"verification failed:\n{feedback}")
            continue
        except Exception as e:  # schema mismatch etc.
            feedback = f"- {type(e).__name__}: {e}"
            print(f"bad spec:\n{feedback}")
            continue
        store.save_spec(spec)
        print(f"saved {path.relative_to(store.ROOT)}")
        return spec, traces
    raise SystemExit(f"gave up on {problem['slug']} after {MAX_ATTEMPTS} attempts")


def scheduled_message(title, slot, url):
    t = slot.publish_at
    when = f"{t:%-I}{t:%p}".lower()
    return f"🎬 {title} goes public {slot.weekday} {when} ET ({t:%b} {t.day}) unless you cancel: {url}"


def run(problem, upload=False, quality="final", schedule=True):
    from shorts.publish import notify
    from shorts.render import render

    try:
        spec, traces = ensure_spec(problem)
    except (VerificationError, SystemExit) as e:
        notify(f"❌ {problem['slug']}: spec failed\n{e}")
        raise
    video = render(spec, traces, quality)
    print(f"rendered {video}")
    if upload:
        from shorts.publish import upload as yt_upload
        slot = None
        if schedule:
            import random
            from datetime import datetime
            from shorts.slots import TZ, pick_slot
            slot = pick_slot(datetime.now(TZ), store.published(), random.Random())
        vid = yt_upload(video, spec.youtube, publish_at=slot.publish_at if slot else None)
        store.mark_published(spec.slug, vid, slot)
        url = f"https://studio.youtube.com/video/{vid}/edit"
        if slot:
            print(f"uploaded (private, public at {slot.publish_at:%a %Y-%m-%d %H:%M %Z}): {url}")
            notify(scheduled_message(spec.title, slot, url), slug=spec.slug, video_id=vid,
                   publish_at=slot.publish_at.isoformat())
        else:
            print(f"uploaded (private): {url}")
            notify(f"🎬 {spec.title} is ready for review: {url}", slug=spec.slug, video_id=vid)
    return video


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["next", "run", "generate", "verify", "render", "report"])
    ap.add_argument("slug", nargs="?")
    ap.add_argument("--upload", action="store_true", help="upload to YouTube as private")
    ap.add_argument("--preview", action="store_true", help="fast low-res render")
    ap.add_argument("--no-schedule", action="store_true",
                    help="upload without a publish time (stays private until you publish it)")
    a = ap.parse_args()
    quality = "preview" if a.preview else "final"

    if a.command == "report":
        from shorts.report import main as report
        report()
        return

    if a.command == "next":
        problem = store.next_problem()
        if problem is None:
            print("queue is empty (or every remaining problem needs a template you haven't built)")
            return
        run(problem, a.upload, quality, schedule=not a.no_schedule)
        return

    if not a.slug:
        ap.error(f"{a.command} needs a slug")
    problem = store.problem(a.slug)
    if a.command == "run":
        run(problem, a.upload, quality, schedule=not a.no_schedule)
    elif a.command == "generate":
        ensure_spec(problem, regenerate=True)
    elif a.command == "verify":
        try:
            traces = verify(store.load_spec(a.slug))
        except VerificationError as e:
            sys.exit(f"FAILED\n{e}")
        print("OK, trace lengths:", [len(t) for t in traces])
    elif a.command == "render":
        from shorts.render import render
        spec = store.load_spec(a.slug)
        print(render(spec, verify(spec), quality))


if __name__ == "__main__":
    main()
