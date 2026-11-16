"""Pieces shared by the pointer-style templates."""
from manim import DOWN, UP, FadeIn, FadeOut, FadeTransform, VGroup

from ..style import BOLD, FG, GREEN, MONO, MUTED, RED, TEAL, T

COMMON_DOC = """  every event: line (int: 0-based body line of `code` to highlight for this step), label (str shown big)
  optional on any event: detail (str, smaller line under the label; cleared when absent),
    best (str, running answer like "best = 5"; stays until replaced), result (str, the final answer, shown green),
    say (blocking caption after the step), say_bg (caption that plays while steps keep going)"""


class Readout:
    """The text block between the array and the code: label / detail-or-result / best."""

    SLOTS = {"label": (UP * 0.9, 40, FG), "detail": (UP * 0.15, 32, MUTED), "best": (DOWN * 0.75, 34, TEAL)}

    def __init__(self, scene):
        self.s, self.mobs = scene, {}

    def anims(self, e, label_color=FG):
        out = []
        for key, (pos, size, color) in self.SLOTS.items():
            text = e.get(key)
            if key == "detail" and e.get("result"):
                text, color, size = e["result"], GREEN, 44
            if key == "label":
                color = label_color
            old = self.mobs.get(key)
            if text is None:
                if key == "detail" and old is not None:
                    out.append(FadeOut(old))
                    del self.mobs[key]
                continue
            new = self.s.fit(T(str(text), size, color, MONO, BOLD)).move_to(pos)
            out.append(FadeIn(new) if old is None else FadeTransform(old, new))
            self.mobs[key] = new
        return out

    def group(self):
        return VGroup(*self.mobs.values())


def label_color(e):
    if e.get("hit") is True or e.get("result"):
        return GREEN
    if e.get("hit") is False or e.get("ok") is False:
        return RED
    return FG


def pace(n, e, fast_after=3):
    """Slow for the first few steps and anything narrated or decisive, fast otherwise."""
    slow = n < fast_after or bool(e.get("say") or e.get("result") or e.get("hit"))
    return slow, (0.55 if slow else 0.3)


def narrate(s, e):
    if e.get("say_bg"):
        s.say(e["say_bg"], wait=False)
    if e.get("say"):
        s.say(e["say"])
