"""Two pointers closing in from both ends. Cells outside [l, r] fade out."""
from manim import FadeIn, VGroup

from ..style import ACC, GREEN, GREEN_FILL, TEAL
from ._common import COMMON_DOC, Readout, label_color, narrate, pace

REQUIRED = {"l", "r", "line", "label"}
HIGHLIGHTS = set()
DOC = """two_pointers: L starts at the left end, R at the right end, and they move toward each other.
  emit per step: l (int), r (int)
  optional: hit (bool: True colors l and r green as the answer, False flashes the label red)
""" + COMMON_DOC


def run(s, spec, ap, trace):
    code = s.code_panel(spec.body_lines(ap), -4.3)
    pl, pr = s.pointer("L", ACC), s.pointer("R", TEAL)
    first = trace[0]
    s.place([(pl, first["l"]), (pr, first["r"])])
    s.play(FadeIn(code), FadeIn(pl), FadeIn(pr), run_time=0.6)
    s.say(ap.intro)

    readout = Readout(s)
    n_cells = len(s.cells)
    for n, e in enumerate(trace):
        l, r = e["l"], e["r"]
        slow, rt = pace(n, e)
        outside = {k for k in range(n_cells) if k < min(l, r) or k > max(l, r)}
        if e.get("hit") is True:
            cells = s.color_cells({l, r}, GREEN, GREEN_FILL, dim=outside)
        else:
            cells = s.color_cells({l, r}, dim=outside)
        s.play(*s.move_ptrs([(pl, l), (pr, r)]), *cells, s.highlight(code, s.line_for(ap, e)),
               *readout.anims(e, label_color(e)), run_time=rt)
        if slow:
            s.wait(0.35)
        narrate(s, e)
    return VGroup(code, pl, pr, readout.group())
