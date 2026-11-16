"""Brute force over pairs: two pointers i < j sweep every pair."""
from manim import DOWN, UP, FadeIn, VGroup

from ..style import ACC, BOLD, GREEN, GREEN_FILL, MONO, MUTED, RED, TEAL, T

REQUIRED = {"i", "j", "label", "hit"}
HIGHLIGHTS = {"check", "hit"}
DOC = """pairs_brute: checks pairs (i, j) one at a time.
  emit per pair: i (int), j (int), label (str shown big, e.g. "3 + 9 = 12"),
    hit (bool: this pair is the answer, or a new best for "max/min over pairs" problems)
  optional: best (str, running answer like "best = 5"), say (blocking caption after the step),
    say_bg (caption that plays while steps keep going)
  the scan stops when traced_code returns, so return on the answer (Two Sum) or scan everything (max profit)
  highlights: check (the comparison line), hit (the return line)"""


def run(s, spec, ap, trace):
    code = s.code_panel(spec.body_lines(ap), -4.3)
    pi, pj = s.pointer("i", ACC), s.pointer("j", TEAL)
    s.at(pi, trace[0]["i"])
    s.at(pj, trace[0]["j"])
    s.play(FadeIn(code), FadeIn(pi), FadeIn(pj), run_time=0.6)
    s.say(ap.intro)

    status = counter = best = None
    for n, e in enumerate(trace):
        i, j, hit = e["i"], e["j"], bool(e["hit"])
        slow = n < 3 or hit
        rt = 0.55 if slow else 0.22
        new_status = s.fit(T(f'{e["label"]}  {"✓" if hit else "✗"}', 44, GREEN if hit else RED, MONO, BOLD)).move_to(UP * 0.9)
        new_counter = T(f"checks: {n + 1}", 28, MUTED, MONO).move_to(UP * 0.1)
        extra = []
        if e.get("best") is not None:
            new_best = s.fit(T(str(e["best"]), 34, TEAL, MONO, BOLD)).move_to(DOWN * 0.75)
            extra.append(s.swap(best, new_best, rt))
            best = new_best
        s.play(s.at(pi.animate, i), s.at(pj.animate, j), *s.color_cells({i, j}),
               s.highlight(code, ap.highlights["hit" if hit else "check"]),
               s.swap(status, new_status, rt), s.swap(counter, new_counter, rt), *extra, run_time=rt)
        status, counter = new_status, new_counter
        if slow:
            s.wait(0.35)
        if hit:
            s.play(*s.color_cells({i, j}, GREEN, GREEN_FILL), run_time=0.3)
        if e.get("say_bg"):
            s.say(e["say_bg"], wait=False)
        if e.get("say"):
            s.say(e["say"])
    return VGroup(code, pi, pj, status, counter, *([best] if best else []))
