"""Scan left to right, pushing onto / popping off a stack drawn as a row (top on the right)."""
from manim import DOWN, LEFT, RIGHT, UP, FadeIn, FadeOut, ReplacementTransform, RoundedRectangle, VGroup

from ..style import ACC, CELL, FG, GREEN, GREEN_FILL, MONO, MUTED, RED, TEAL, T
from ._common import COMMON_DOC, Readout, label_color, narrate, pace

REQUIRED = {"i", "line", "label", "action"}
HIGHLIGHTS = set()
DOC = """stack: pointer i scans the array; a stack (bottom left, top right) grows and shrinks below it.
  emit per element: i (int), action ("push" | "pop" | "none")
  for push: value (str, what goes on the stack, max ~4 chars)
  for pop: ok (bool, False = mismatch/failure, flashes red)
  the stack row is drawn where `best` would go, so don't use best with this template.
""" + COMMON_DOC


def run(s, spec, ap, trace):
    code = s.code_panel(spec.body_lines(ap), -4.3)
    pi = s.pointer("i", ACC)
    s.place([(pi, trace[0]["i"])])
    lbl = T(ap.memory_label if ap.memory_label != "seen" else "stack", 28, MUTED, MONO)
    lbl.move_to(LEFT * 3.75 + DOWN * 0.45, aligned_edge=LEFT)
    s.play(FadeIn(code), FadeIn(pi), FadeIn(lbl), run_time=0.6)
    s.say(ap.intro)

    chip_w = min(1.0, 7.5 / max(1, len(s.cells)) - 0.1)
    readout = Readout(s)
    readout.SLOTS = {k: v for k, v in Readout.SLOTS.items() if k != "best"}
    stack = []
    for n, e in enumerate(trace):
        i, action = e["i"], e["action"]
        slow, rt = pace(n, e)
        if e.get("ok") is False:
            slow, rt = True, 0.55
        anims = [*s.move_ptrs([(pi, i)]), *s.color_cells({i}), s.highlight(code, s.line_for(ap, e)),
                 *readout.anims(e, label_color(e))]

        if action == "push":
            box = RoundedRectangle(corner_radius=0.12, width=chip_w, height=0.7, stroke_color=TEAL,
                                   stroke_width=3, fill_color=CELL, fill_opacity=1)
            chip = VGroup(box, s.fit(T(str(e.get("value", "?")), 28, FG, MONO), chip_w - 0.15).move_to(box))
            chip.move_to(LEFT * 3.75 + DOWN * 1.25, aligned_edge=LEFT).shift(RIGHT * len(stack) * (chip_w + 0.1))
            anims.append(ReplacementTransform(s.cells[i][1].copy(), chip))
            stack.append(chip)
            s.play(*anims, run_time=rt + 0.1)
        elif action == "pop" and stack:
            top = stack.pop()
            good = e.get("ok") is not False
            color, fill = (GREEN, GREEN_FILL) if good else (RED, "#3A1618")
            s.play(*anims, top[0].animate.set_stroke(color, 5).set_fill(fill), run_time=rt)
            s.play(FadeOut(top, shift=UP * 0.4), run_time=0.25 if not slow else 0.4)
        else:
            s.play(*anims, run_time=rt)

        if slow:
            s.wait(0.3)
        narrate(s, e)
    return VGroup(code, pi, lbl, VGroup(*stack), readout.group())
