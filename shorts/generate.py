"""Ask Claude for a spec. Output is forced through a tool whose input schema is
the Spec model, then validated by pydantic and checked by verify.py."""
import copy
import os

import anthropic

from .spec import Spec
from .store import spec_path
from .templates import TEMPLATES

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5")

RULES = """You write specs for a YouTube Shorts channel that animates LeetCode solutions.
Return the spec through the submit_spec tool.

Hard rules:
- Describe the problem in your OWN words. Never copy LeetCode's statement, examples or constraints.
- Pick a fresh example (not LeetCode's): the drawn list or string has 4-10 items, and every trace stays under 25 events.
- Use only the templates listed for this problem, in that order (usually brute force first, then the optimal one).
- `code` is clean, idiomatic Python that is shown on screen: the def line is hidden, body lines <= 38 chars.
- `traced_code` is the SAME algorithm with emit(**event) calls using exactly the event keys the template documents.
- Code-line indices (`highlights`, or an event's `line`) are 0-based into the function BODY of `code` (the def line is not counted).
- A problem with one approach is fine: name it after the technique (e.g. "Two pointers").
- tests: 5+ cases including edge cases, and include the example itself. Set `compare` so valid answers pass.
- Captions are short: at most ~34 chars per line, use \\n for a second line. Put the narration's personality in them.
- The hook must be different from the reference spec's: same punchy energy, new wording, about this problem.
- Add a few `say` / `say_bg` lines in traced_code on early steps and on the answer step, like the reference.
- YouTube title <= 90 chars and ends with #shorts.
"""


def _inline_refs(schema):
    """Anthropic tool schemas are safest without $ref; inline pydantic's $defs."""
    defs = schema.pop("$defs", {})

    def walk(node):
        if isinstance(node, dict):
            if "$ref" in node:
                return walk(copy.deepcopy(defs[node["$ref"].split("/")[-1]]))
            return {k: walk(v) for k, v in node.items()}
        if isinstance(node, list):
            return [walk(v) for v in node]
        return node

    return walk(schema)


def generate(problem: dict, feedback: str | None = None) -> Spec:
    templates = "\n\n".join(TEMPLATES[t].DOC for t in problem["templates"])
    reference = spec_path("two-sum").read_text()
    prompt = (f"{RULES}\nProblem: LeetCode #{problem['number']} {problem['title']} (slug: {problem['slug']})\n"
              f"Templates, in order: {problem['templates']}\n\nTemplate docs:\n{templates}\n\n"
              f"Reference spec for a different problem (match its style, not its content):\n```yaml\n{reference}```")
    if feedback:
        prompt += f"\n\nYour previous attempt failed verification. Fix these problems:\n{feedback}"

    msg = anthropic.Anthropic().messages.create(
        model=MODEL,
        max_tokens=8000,
        tools=[{"name": "submit_spec", "description": "Submit the finished video spec.",
                "input_schema": _inline_refs(Spec.model_json_schema())}],
        tool_choice={"type": "tool", "name": "submit_spec"},
        messages=[{"role": "user", "content": prompt}],
    )
    data = next(b.input for b in msg.content if b.type == "tool_use")
    data.update(slug=problem["slug"], number=problem["number"])
    return Spec.model_validate(data)
