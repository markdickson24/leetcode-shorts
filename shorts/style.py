"""Channel look: palette, fonts and the text helper. Change these to restyle every video."""
from manim import BOLD, NORMAL, Text

BG, FG, MUTED = "#0E1116", "#F1F1F1", "#7A8290"
CELL, GREEN_FILL = "#1B2230", "#163A27"
ACC, TEAL, RED, GREEN = "#FF9F1C", "#2EC4B6", "#FF5A5F", "#3DDC84"
SANS, MONO = "Inter", "DejaVu Sans Mono"

__all__ = ["BG", "FG", "MUTED", "CELL", "GREEN_FILL", "ACC", "TEAL", "RED", "GREEN",
           "SANS", "MONO", "BOLD", "NORMAL", "T"]


def T(s, size=36, color=FG, font=SANS, weight=NORMAL):
    return Text(s, font=font, font_size=size, color=color, weight=weight)
