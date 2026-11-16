"""Binary search: L, M, R pointers; the discarded half fades out each step."""
from manim import FadeIn, VGroup

from ..style import ACC, GREEN, GREEN_FILL, RED, TEAL
from ._common import COMMON_DOC, Readout, label_color, narrate, pace

REQUIRED = {"l", "r", "m", "line", "label"}
HIGHLIGHTS = set()
DOC = """binary_search: search range [l, r] with midpoint m; everything outside [l, r] is faded.
  emit per step: l (int), r (int), m (int, must be a valid index)
  optional: hit (bool: True colors m green as the answer)
""" + COMMON_DOC


def run(s, spec, ap, trace):
    code = s.code_panel(spec.body_lines(ap), -4.3)
    pl, pm, pr = s.pointer("L", TEAL), s.pointer("M", ACC), s.pointer("R", RED)
    first = trace[0]
    s.place([(pl, first["l"]), (pm, first["m"]), (pr, first["r"])])
    s.play(FadeIn(code), FadeIn(pl), FadeIn(pm), FadeIn(pr), run_time=0.6)
    s.say(ap.intro)

    readout = Readout(s)
    n_cells = len(s.cells)
    for n, e in enumerate(trace):
        l, m, r = e["l"], e["m"], e["r"]
        slow, rt = pace(n, e, fast_after=n_cells)  # binary search is short; keep it readable
        outside = {k for k in range(n_cells) if k < l or k > r}
        if e.get("hit") is True:
            cells = s.color_cells({m}, GREEN, GREEN_FILL, dim=outside)
        else:
            cells = s.color_cells({m}, dim=outside)
        s.play(*s.move_ptrs([(pl, l), (pm, m), (pr, r)]), *cells, s.highlight(code, s.line_for(ap, e)),
               *readout.anims(e, label_color(e)), run_time=rt)
        if slow:
            s.wait(0.35)
        narrate(s, e)
    return VGroup(code, pl, pm, pr, readout.group())
