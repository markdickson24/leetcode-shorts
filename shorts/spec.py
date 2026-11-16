"""The video spec: everything one Short needs, as data.

Claude produces this (or you hand-write it in specs/<slug>.yaml). It never
contains Manim code: templates turn it into animation.
"""
from typing import Any, Literal

from pydantic import BaseModel, Field

# Keep in sync with shorts/templates/__init__.py (a test checks this).
TemplateName = Literal["pairs_brute", "hashmap_scan", "two_pointers", "sliding_window", "stack", "binary_search"]


class Hook(BaseModel):
    top: str = Field(description="On-screen line 1, max ~20 chars, e.g. \"Can't solve this?\"")
    bottom: str = Field(description="On-screen punchline, max ~18 chars, e.g. \"Start studying.\"")
    spoken_top: str = Field(description="What the voice says while line 1 shows")
    spoken_bottom: str = Field(description="What the voice says as the punchline lands")


class Case(BaseModel):
    args: dict[str, Any] = Field(description="Keyword arguments for the solution function")
    expected: Any


class Approach(BaseModel):
    name: str = Field(description='Short label, e.g. "Brute force", "HashMap"')
    template: TemplateName
    time: str = Field(description='e.g. "O(n²)"')
    space: str = Field(description='e.g. "O(1)"')
    code: str = Field(description="Clean, runnable Python function shown on screen. Body lines <= 38 chars.")
    traced_code: str = Field(description="Same algorithm, calling emit(**event) per step with the template's event keys")
    highlights: dict[str, int] = Field(
        description="Template phase -> 0-based line index in the function BODY (the def line is not shown). "
                    "{} for templates whose events carry their own `line`.")
    intro: str = Field(description="Caption said when this approach starts. Use \\n to split into 2 lines.")
    verdict: str = Field(description="Caption after it finishes. May use {steps} and {first_steps}.")
    memory_label: str = Field("seen", description="Name of the hash map / set shown on screen")


class YouTubeMeta(BaseModel):
    title: str = Field(description="<= 90 chars, include #shorts")
    description: str
    tags: list[str]


class Spec(BaseModel):
    slug: str
    number: int
    title: str
    function_name: str
    hook: Hook
    statement: str = Field(description="The problem in YOUR OWN words, 1-2 caption lines. Never copy LeetCode text.")
    array_arg: str = Field(description="Which argument (a list or a string) is drawn as cells on screen")
    show_args: list[str] = Field(description='Other arguments to display, e.g. ["target"]')
    example: Case = Field(description="The animated example. The drawn list/string has 4-10 items.")
    tests: list[Case] = Field(description="5+ cases incl. edge cases; the example should be one of them")
    compare: Literal["exact", "sorted", "set"] = Field(
        "exact", description="sorted: order of a list doesn't matter; set: order of a list of lists doesn't matter")
    approaches: list[Approach] = Field(min_length=1, max_length=3)
    challenge: str = Field(description="Pause-and-think line before the better approach")
    outro: list[str] = Field(description="1-2 closing captions, the last one should invite comments")
    cta: str = "Follow for a new problem daily"
    youtube: YouTubeMeta

    def body_lines(self, ap: Approach) -> list[str]:
        """The function body, dedented: what appears in the code panel."""
        lines = ap.code.strip("\n").splitlines()
        body = [l for l in lines[1:] if l.strip()]
        indent = min(len(l) - len(l.lstrip()) for l in body)
        return [l[indent:] for l in body]
