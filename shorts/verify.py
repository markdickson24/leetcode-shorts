"""Prove a spec is correct before anything gets rendered.

Runs every approach's code against the tests in a separate Python process,
runs the traced version on the example, and checks the trace has what its
template needs. Returns one trace per approach.
"""
import json
import subprocess
import sys

from .spec import Spec
from .templates import TEMPLATES

MAX_TRACE = 30          # longer than this won't fit in a Short
TIMEOUT_S = 10

# Executed with `python -I` in a child process. Spec code is LLM-written, so it
# never runs inside the pipeline process itself.
_RUNNER = r"""
import json, sys
req = json.load(sys.stdin)
g = {}
exec(req["code"], g)
fn = g[req["fn"]]
results = []
for case in req["cases"]:
    try:
        results.append({"ok": True, "value": fn(**case)})
    except Exception as e:
        results.append({"ok": False, "error": f"{type(e).__name__}: {e}"})
events = []
g2 = {"emit": lambda **kw: events.append(kw)}
exec(req["traced_code"], g2)
traced = g2[req["fn"]](**req["example"])
print(json.dumps({"results": results, "traced": traced, "trace": events}, default=str))
"""


class VerificationError(Exception):
    pass


def _norm(v, mode):
    if mode == "sorted" and isinstance(v, list):
        return sorted(v, key=json.dumps)
    if mode == "set" and isinstance(v, list):
        return sorted((_norm(x, "sorted") for x in v), key=json.dumps)
    return v


def _run(spec, ap):
    req = {"code": ap.code, "traced_code": ap.traced_code, "fn": spec.function_name,
           "cases": [c.args for c in spec.tests], "example": spec.example.args}
    try:
        proc = subprocess.run([sys.executable, "-I", "-c", _RUNNER], input=json.dumps(req),
                              capture_output=True, text=True, timeout=TIMEOUT_S)
    except subprocess.TimeoutExpired:
        raise VerificationError(f"{ap.name}: timed out after {TIMEOUT_S}s")
    if proc.returncode != 0:
        raise VerificationError(f"{ap.name}: crashed:\n{proc.stderr.strip()[-1500:]}")
    return json.loads(proc.stdout)


def verify(spec: Spec) -> list[list[dict]]:
    problems, traces = [], []
    ex = spec.example.args
    arr = ex.get(spec.array_arg)
    if not isinstance(arr, (list, str)) or not 3 <= len(arr) <= 10:
        problems.append(f"example.args[{spec.array_arg!r}] must be a list or string of 3-10 items")
    for a in spec.show_args:
        if a not in ex:
            problems.append(f"show_args has {a!r}, which isn't in example.args")
    if not any(c.args == ex for c in spec.tests):
        problems.append("the example should also be one of the tests")

    for ap in spec.approaches:
        tpl = TEMPLATES[ap.template]
        n_lines = len(spec.body_lines(ap))
        for key in tpl.HIGHLIGHTS - ap.highlights.keys():
            problems.append(f"{ap.name}: highlights is missing {key!r}")
        for key, line in ap.highlights.items():
            if not 0 <= line < n_lines:
                problems.append(f"{ap.name}: highlight {key!r}={line} is outside the {n_lines} body lines")
        too_long = [l for l in spec.body_lines(ap) if len(l) > 40]
        if too_long:
            problems.append(f"{ap.name}: code lines over 40 chars won't be readable: {too_long}")

        try:
            out = _run(spec, ap)
        except VerificationError as e:
            problems.append(str(e))
            traces.append([])
            continue

        for case, res in zip(spec.tests, out["results"]):
            if not res["ok"]:
                problems.append(f"{ap.name}: {case.args} raised {res['error']}")
            elif _norm(res["value"], spec.compare) != _norm(case.expected, spec.compare):
                problems.append(f"{ap.name}: {case.args} returned {res['value']!r}, expected {case.expected!r}")
        if _norm(out["traced"], spec.compare) != _norm(spec.example.expected, spec.compare):
            problems.append(f"{ap.name}: traced_code returned {out['traced']!r} on the example, "
                            f"expected {spec.example.expected!r}")

        trace = out["trace"]
        if not 1 <= len(trace) <= MAX_TRACE:
            problems.append(f"{ap.name}: trace has {len(trace)} events (need 1-{MAX_TRACE}); use a smaller example")
        for n, e in enumerate(trace):
            missing = tpl.REQUIRED - e.keys()
            if missing:
                problems.append(f"{ap.name}: event {n} is missing {sorted(missing)}")
                break
            for k in ("i", "j", "m", "match"):
                if e.get(k) is not None and isinstance(arr, (list, str)) and not 0 <= e[k] < len(arr):
                    problems.append(f"{ap.name}: event {n} has {k}={e[k]} outside the array")
            if e.get("line") is not None and not 0 <= e["line"] < n_lines:
                problems.append(f"{ap.name}: event {n} has line={e['line']} outside the {n_lines} body lines")
        traces.append(trace)

    if problems:
        raise VerificationError("\n".join(f"- {p}" for p in problems))
    return traces
