"""The Short's skeleton: hook -> problem -> approaches (via templates) -> outro.

Shared building blocks live here; per-algorithm animation lives in templates/.
"""
from manim import (DOWN, LEFT, RIGHT, TAU, UP, FadeIn, FadeOut, FadeTransform, LaggedStart, MoveToTarget,
                   Paragraph, Rectangle, RoundedRectangle, Scene, Triangle, VGroup, Wiggle)

from .style import ACC, BOLD, CELL, FG, GREEN, MONO, MUTED, RED, SANS, TEAL, T
from .templates import TEMPLATES
from .tts import synth

PHASE_COLORS = [RED, ACC, GREEN]


class ShortScene(Scene):
    spec = None    # set by render.py before .render()
    traces = None

    # ---------- building blocks (used by templates) ----------
    def fit(self, mob, max_w=8.4):
        if mob.width > max_w:
            mob.scale_to_fit_width(max_w)
        return mob

    def build_array(self, values):
        values = ["␣" if ch == " " else ch for ch in values] if isinstance(values, str) else values
        n = len(values)
        size = min(1.2, (8.4 - 0.15 * (n - 1)) / n)
        cells = VGroup()
        for v in values:
            box = RoundedRectangle(corner_radius=0.15, width=size, height=size, stroke_color=FG,
                                   stroke_width=3, fill_color=CELL, fill_opacity=1)
            cells.add(VGroup(box, self.fit(T(str(v), 46, weight=BOLD), size - 0.2).move_to(box)))
        cells.arrange(RIGHT, buff=0.15).move_to(UP * 3.5)
        idx = VGroup(*[T(str(k), 26, MUTED, MONO).next_to(c, DOWN, buff=0.15) for k, c in enumerate(cells)])
        return cells, idx

    def pointer(self, label, color):
        tri = Triangle(fill_color=color, fill_opacity=1, stroke_width=0).scale(0.17)
        return VGroup(tri, T(label, 30, color, MONO, BOLD).next_to(tri, DOWN, buff=0.06))

    def at(self, ptr, k):
        return ptr.next_to(self.idx[k], DOWN, buff=0.12)

    def ptr_spots(self, pairs):
        """[(pointer, index)] -> [(pointer, point)], spreading pointers that share a cell."""
        n = len(self.cells)
        pairs = [(p, min(max(int(k), 0), n - 1)) for p, k in pairs]
        out = []
        for p, k in pairs:
            same = [q for q, kk in pairs if kk == k]
            dx = (same.index(p) - (len(same) - 1) / 2) * 0.42
            y = self.idx[k].get_bottom()[1] - 0.12 - p.height / 2
            out.append((p, [self.idx[k].get_x() + dx, y, 0]))
        return out

    def place(self, pairs):
        for p, pt in self.ptr_spots(pairs):
            p.move_to(pt)

    def move_ptrs(self, pairs):
        return [p.animate.move_to(pt) for p, pt in self.ptr_spots(pairs)]

    def line_for(self, ap, e, phase=None):
        """Code line for this step: the event's own `line`, else the approach's phase mapping."""
        return e["line"] if e.get("line") is not None else ap.highlights[phase]

    def code_panel(self, lines, center_y):
        cw = T("M" * 10, 24, font=MONO).width / 10
        rows = VGroup()
        for n, line in enumerate(lines):
            indent = len(line) - len(line.lstrip())
            t = T(line.strip(), 24, FG, MONO)
            t.move_to([0, 0, 0], aligned_edge=LEFT).shift(RIGHT * indent * cw + DOWN * n * 0.52)
            rows.add(t)
        self.fit(rows, 7.9)
        if rows.height > 3.6:  # long functions shrink to fit between the readout and the captions
            rows.scale_to_fit_height(3.6)
        h = rows.height + 0.7
        center_y = max(-6.2 + h / 2, min(center_y, -1.75 - h / 2))
        rows.move_to(UP * center_y)
        bg = RoundedRectangle(corner_radius=0.2, width=8.6, height=h, fill_color="#161B22",
                              fill_opacity=1, stroke_color="#2A313C", stroke_width=2).move_to(rows)
        rows.align_to(bg, LEFT).shift(RIGHT * 0.35)
        hl = Rectangle(width=8.4, height=0.46, fill_color=ACC, fill_opacity=0, stroke_width=0).move_to(bg)
        hl.set_y(rows[0].get_y())
        return VGroup(bg, hl, rows)

    def highlight(self, panel, line):
        _, hl, rows = panel
        y = rows[line].get_y()
        if hl.get_fill_opacity() == 0:
            hl.set_y(y)
            return hl.animate.set_fill(opacity=0.22)
        return hl.animate.set_y(y)

    def swap(self, old, new, rt=0.3):
        return FadeIn(new, run_time=rt) if old is None else FadeTransform(old, new, run_time=rt)

    def color_cells(self, active, color=ACC, fill=CELL, dim=()):
        """Highlight `active` cells, fade `dim` ones (ruled out), reset the rest."""
        anims = []
        for k, c in enumerate(self.cells):
            on, op = k in active, 0.22 if k in dim else 1.0
            c.generate_target()
            c.target.set_opacity(op)
            c.target[0].set_stroke(color if on else FG, 6 if on else 3, opacity=op)
            c.target[0].set_fill(fill if on else CELL, opacity=op)
            anims.append(MoveToTarget(c))
        return anims

    def say(self, s, wait=True, spoken=None):
        """Caption + voice. wait=False keeps animating under the narration.
        s=None speaks without a caption (the visuals already show the words)."""
        self.wait_for_voice()  # never talk over the previous line
        path, dur = synth(spoken or s)
        self.add_sound(path)
        self.voice_until = self.time + dur + 0.25
        if s is not None:
            new = Paragraph(*s.split("\n"), alignment="center", font=SANS, font_size=36,
                            color=FG, line_spacing=0.8)
            self.fit(new).move_to(DOWN * 6.9)
            anims = [FadeIn(new, shift=UP * 0.2)]
            if self.cap is not None:
                anims.append(FadeOut(self.cap, shift=UP * 0.2))
            self.play(*anims, run_time=0.35)
            self.cap = new
        if wait:
            self.wait_for_voice()

    def wait_for_voice(self):
        if self.voice_until - self.time > 0.07:
            self.wait(self.voice_until - self.time)

    # ---------- the video ----------
    def construct(self):
        spec, traces = self.spec, self.traces
        self.cap, self.voice_until = None, 0.0
        ex = spec.example.args

        title = self.fit(T(spec.title, 84, ACC, weight=BOLD)).move_to(UP * 7.0)
        tag = T(f"LeetCode #{spec.number}", 26, MUTED).next_to(title, DOWN, buff=0.12)
        self.cells, self.idx = self.build_array(ex[spec.array_arg])
        shown = "   ".join(f"{a} = {ex[a]}" for a in spec.show_args)
        args_txt = self.fit(T(shown, 40, TEAL, MONO, BOLD)).move_to(UP * 5.0) if shown else VGroup()

        # Hook: everything on screen from frame 1, no slow intro.
        self.add(title, tag, self.cells, self.idx, args_txt)
        h1 = self.fit(T(spec.hook.top, 66, FG, weight=BOLD))
        h2 = self.fit(T(spec.hook.bottom, 80, RED, weight=BOLD))
        hook = VGroup(h1, h2).arrange(DOWN, buff=0.35).move_to(DOWN * 0.6)
        self.play(FadeIn(h1, scale=1.25), run_time=0.25)
        self.say(None, spoken=spec.hook.spoken_top)
        self.play(FadeIn(h2, scale=1.8), run_time=0.2)
        self.say(None, spoken=spec.hook.spoken_bottom, wait=False)
        self.play(Wiggle(h2, scale_value=1.08, rotation_angle=0.04 * TAU), run_time=0.6)
        self.wait_for_voice()
        self.play(FadeOut(hook, scale=0.8), run_time=0.3)
        self.say(spec.statement)

        phase, stage = tag, None
        last = len(spec.approaches) - 1
        for k, (ap, trace) in enumerate(zip(spec.approaches, traces)):
            if k > 0:
                self.say(spec.challenge)
                self.countdown()
            color = GREEN if k == last else PHASE_COLORS[min(k, 1)]
            name = ap.name if last == 0 else f"{k + 1} · {ap.name}"
            new_phase = T(name, 34, color, weight=BOLD).move_to(UP * 5.85)
            out = [FadeTransform(phase, new_phase)] + self.color_cells(set())
            if stage is not None:
                out.append(FadeOut(stage))
            self.play(*out, run_time=0.6)
            phase = new_phase
            stage = TEMPLATES[ap.template].run(self, spec, ap, trace)
            self.say(ap.verdict.format(steps=len(trace), first_steps=len(traces[0])))

        self.outro(stage)

    def countdown(self):
        for k in (3, 2, 1):
            num = T(str(k), 120, ACC, weight=BOLD).move_to(DOWN * 1.3)
            self.play(FadeIn(num, scale=1.6), run_time=0.15)
            self.play(FadeOut(num, scale=0.6), run_time=0.45)

    def outro(self, stage):
        spec = self.spec
        self.play(FadeOut(stage), *self.color_cells(set()), run_time=0.5)
        rows = []
        for k, ap in enumerate(spec.approaches):
            color = GREEN if k == len(spec.approaches) - 1 else PHASE_COLORS[min(k, 1)]
            rows.append(VGroup(T(ap.name, 34, color, weight=BOLD),
                               T(f"{ap.time} time · {ap.space} space", 28, FG, MONO)).arrange(DOWN, buff=0.18))
        card = VGroup(*rows).arrange(DOWN, buff=0.7).move_to(DOWN * 1.2)
        self.play(LaggedStart(*[FadeIn(r, shift=UP * 0.3) for r in card], lag_ratio=0.4), run_time=1.0)
        for n, line in enumerate(spec.outro):
            if n == len(spec.outro) - 1:
                cta = self.fit(T(spec.cta, 34, ACC, weight=BOLD)).move_to(DOWN * 4.6)
                self.play(FadeIn(cta, shift=UP * 0.3), run_time=0.4)
            self.say(line)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.6)
