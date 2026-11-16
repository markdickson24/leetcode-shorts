"""One pass with a hash map / set: look up, then remember."""
from manim import DOWN, LEFT, RIGHT, UP, FadeIn, FadeOut, FadeTransform, ReplacementTransform, RoundedRectangle, VGroup

from ..style import ACC, BOLD, CELL, FG, GREEN, GREEN_FILL, MONO, MUTED, RED, TEAL, T

REQUIRED = {"i", "label", "query", "found"}
HIGHLIGHTS = {"init", "compute", "lookup", "found", "store"}
DOC = """hashmap_scan: walks the array once with pointer i, checking a hash map/set.
  emit per element: i (int), label (str, e.g. "need = 15 − 3 = 12"), query (str, e.g. "12 in seen?"),
    found (bool: the lookup succeeded)
  when found is false and something is stored: store (str chip text, e.g. "3→0" or "3")
  when found is true: match (int: array index whose stored chip matched), result (str, e.g. "return [4, 5]")
  optional: say (blocking caption after the step), say_bg (caption that plays while steps keep going)
  highlights: init (map creation), compute (label line), lookup (the `in` check), found (return), store (insert)"""


def run(s, spec, ap, trace):
    code = s.code_panel(spec.body_lines(ap), -4.25)
    pi = s.pointer("i", ACC)
    s.at(pi, trace[0]["i"])
    mem_lbl = T(ap.memory_label, 28, MUTED, MONO).move_to(LEFT * 3.75 + DOWN * 0.2, aligned_edge=LEFT)
    empty = T("{ }", 30, MUTED, MONO).next_to(mem_lbl, DOWN, buff=0.25).align_to(mem_lbl, LEFT)
    s.play(FadeIn(code), FadeIn(pi), FadeIn(mem_lbl), FadeIn(empty), run_time=0.5)
    s.play(s.highlight(code, ap.highlights["init"]), run_time=0.3)
    s.say(ap.intro)

    n_cells = len(s.cells)
    chip_w = min(1.3, 7.5 / max(1, n_cells - 1) - 0.12)
    chips, status, result = VGroup(), None, None
    for n, e in enumerate(trace):
        i, found = e["i"], bool(e["found"])
        slow = n < 2 or found or bool(e.get("say"))
        rt = 0.5 if slow else 0.25

        new_status = s.fit(T(e["label"], 40, FG, MONO, BOLD)).move_to(UP * 0.9)
        s.play(s.at(pi.animate, i), *s.color_cells({i}), s.highlight(code, ap.highlights["compute"]),
               s.swap(status, new_status, rt), run_time=rt)
        status = new_status
        if e.get("say_bg"):
            s.say(e["say_bg"], wait=False)

        lookup = s.fit(T(f'{e["query"]}  {"✓" if found else "✗"}', 36, GREEN if found else RED, MONO, BOLD)).move_to(UP * 0.15)
        s.play(s.highlight(code, ap.highlights["lookup"]), FadeIn(lookup, shift=UP * 0.1), run_time=rt)
        if slow:
            s.wait(0.3)

        if found:
            j = e.get("match")
            anims = [s.highlight(code, ap.highlights["found"])]
            hit = next((c for c in chips if c.src == j), None)
            if hit is not None:
                anims.append(hit[0].animate.set_stroke(GREEN, 5).set_fill(GREEN_FILL))
            anims += s.color_cells({i} | ({j} if j is not None else set()), GREEN, GREEN_FILL)
            s.play(*anims, run_time=0.5)
            if e.get("say"):
                s.say(e["say"])
            if e.get("result"):
                result = s.fit(T(e["result"], 44, GREEN, MONO, BOLD)).move_to(UP * 0.15)
                s.play(FadeTransform(lookup, result), run_time=0.4)
                lookup = None
            s.wait(0.6)
            break

        anims = [FadeOut(lookup)]
        if e.get("store") is not None:
            box = RoundedRectangle(corner_radius=0.12, width=chip_w, height=0.68, stroke_color=TEAL,
                                   stroke_width=3, fill_color=CELL, fill_opacity=1)
            chip = VGroup(box, s.fit(T(str(e["store"]), 26, FG, MONO), chip_w - 0.15).move_to(box))
            chip.src = i
            chip.move_to(LEFT * 3.75 + DOWN * 0.95, aligned_edge=LEFT).shift(RIGHT * len(chips) * (chip_w + 0.12))
            anims += [s.highlight(code, ap.highlights["store"]), ReplacementTransform(s.cells[i][1].copy(), chip)]
            if len(chips) == 0:
                anims.append(FadeOut(empty))
            chips.add(chip)
        s.play(*anims, run_time=rt + 0.15)
        if e.get("say"):
            s.say(e["say"])

    leftovers = [m for m in (lookup,) if m is not None]
    if len(chips) == 0:
        leftovers.append(empty)
    return VGroup(code, pi, mem_lbl, chips, status, *(m for m in (result,) if m), *leftovers)
