"""LeetCode Shorts pipeline.

  python pipeline.py next [--upload]           next problem in the queue, end to end
  python pipeline.py run <slug> [--upload]     one problem, end to end
  python pipeline.py generate <slug>           (re)write specs/<slug>.yaml with Claude
  python pipeline.py verify <slug>             test the spec's code and traces
  python pipeline.py render <slug> [--preview] render without uploading

End to end = spec (saved one, or generate + retry until it verifies) -> verify -> render
-> upload as PRIVATE -> ping you to review. Nothing goes public without you.
"""
import argparse
import sys

from shorts import store
from shorts.verify import VerificationError, verify

MAX_ATTEMPTS = 3


def ensure_spec(problem, regenerate=False):
    """Load a saved spec, or have Claude write one, feeding failures back until it verifies."""
    path = store.spec_path(problem["slug"])
    if path.exists() and not regenerate:
        spec = store.load_spec(problem["slug"])
        return spec, verify(spec)

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


def run(problem, upload=False, quality="final"):
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
        vid = yt_upload(video, spec.youtube)
        store.mark_published(spec.slug, vid)
        url = f"https://studio.youtube.com/video/{vid}/edit"
        print(f"uploaded (private): {url}")
        notify(f"🎬 {spec.title} is ready for review: {url}", slug=spec.slug, video_id=vid)
    return video


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["next", "run", "generate", "verify", "render"])
    ap.add_argument("slug", nargs="?")
    ap.add_argument("--upload", action="store_true", help="upload to YouTube as private")
    ap.add_argument("--preview", action="store_true", help="fast low-res render")
    a = ap.parse_args()
    quality = "preview" if a.preview else "final"

    if a.command == "next":
        problem = store.next_problem()
        if problem is None:
            print("queue is empty (or every remaining problem needs a template you haven't built)")
            return
        run(problem, a.upload, quality)
        return

    if not a.slug:
        ap.error(f"{a.command} needs a slug")
    problem = store.problem(a.slug)
    if a.command == "run":
        run(problem, a.upload, quality)
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
