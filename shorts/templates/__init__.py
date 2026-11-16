"""Scene templates. Each module exposes REQUIRED (event keys), HIGHLIGHTS
(code-line phases), DOC (fed to Claude) and run(scene, spec, approach, trace).

To add one (two pointers, sliding window, stack, tree, DP grid...):
  1. write shorts/templates/<name>.py following pairs_brute.py
  2. register it below and add the name to TemplateName in shorts/spec.py
  3. list it under a problem's `templates` in problems.yaml
"""
from . import binary_search, hashmap_scan, pairs_brute, sliding_window, stack, two_pointers

TEMPLATES = {
    "pairs_brute": pairs_brute,
    "hashmap_scan": hashmap_scan,
    "two_pointers": two_pointers,
    "sliding_window": sliding_window,
    "stack": stack,
    "binary_search": binary_search,
}
