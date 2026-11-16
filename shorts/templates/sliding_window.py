"""A window [l, r] that grows on the right and shrinks on the left, boxed on screen."""
from manim import FadeIn, ReplacementTransform, SurroundingRectangle, VGroup

from ..style import ACC, GREEN, GREEN_FILL, TEAL
from ._common import COMMON_DOC, Readout, label_color, narrate, pace

REQUIRED = {"l", "r", "line", "label"}
HIGHLIGHTS = set()
DOC = """sliding_window: a window from index l to r (inclusive) is boxed; R expands it, L shrinks it.
  Also fits "track the best so far" scans (e.g. l = cheapest buy day so far, r = today).
  emit per step: l (int), r (int)
  optional: hit (bool: True colors the window green, e.g. a new best)
""" + COMMON_DOC


def _box(s, l, r, color):
    lo, hi = sorted((max(l, 0), min(r, len(s.cells) - 1)))
    return SurroundingRectangle(VGroup(*s.cells[lo:hi + 1]), color=color, buff=0.1,
                                corner_radius=0.2, stroke_width=5)


def run(s, spec, ap, trace):
    code = s.code_panel(spec.body_lines(ap), -4.3)
    pl, pr = s.pointer("L", ACC), s.pointer("R", TEAL)
    first = trace[0]
    s.place([(pl, first["l"]), (pr, first["r"])])
    box = _box(s, first["l"], first["r"], ACC)
    s.play(FadeIn(code), FadeIn(pl), FadeIn(pr), FadeIn(box), run_time=0.6)
    s.say(ap.intro)

    readout = Readout(s)
    for n, e in enumerate(trace):
        l, r = e["l"], e["r"]
        slow, rt = pace(n, e)
        hit = e.get("hit") is True
        new_box = _box(s, l, r, GREEN if hit else ACC)
        lo, hi = sorted((l, r))
        inside = set(range(max(lo, 0), min(hi, len(s.cells) - 1) + 1))
        cells = s.color_cells(inside, GREEN, GREEN_FILL) if hit else s.color_cells(set())
        s.play(*s.move_ptrs([(pl, l), (pr, r)]), ReplacementTransform(box, new_box), *cells,
               s.highlight(code, s.line_for(ap, e)), *readout.anims(e, label_color(e)), run_time=rt)
        box = new_box
        if slow:
            s.wait(0.35)
        narrate(s, e)
    return VGroup(code, pl, pr, box, readout.group())
