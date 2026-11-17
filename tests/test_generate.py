from types import SimpleNamespace

import pytest
import yaml

from shorts import generate as gen
from shorts import store


class FakeClient:
    """Records the request; replies with the given content blocks."""

    def __init__(self, content, stop_reason="tool_use"):
        self.kwargs, self.reply = None, SimpleNamespace(content=content, stop_reason=stop_reason)
        self.messages = self

    def create(self, **kwargs):
        self.kwargs = kwargs
        return self.reply


PROBLEM = {"slug": "two-sum", "number": 1, "title": "Two Sum", "templates": ["pairs_brute", "hashmap_scan"]}


def test_does_not_force_tool_choice(monkeypatch):
    spec = yaml.safe_load(store.spec_path("two-sum").read_text())
    fake = FakeClient([SimpleNamespace(type="tool_use", name="submit_spec", input=spec)])
    monkeypatch.setattr(gen.anthropic, "Anthropic", lambda: fake)
    assert gen.generate(PROBLEM).slug == "two-sum"
    assert fake.kwargs.get("tool_choice", {"type": "auto"})["type"] == "auto"


def test_missing_tool_call_is_a_clear_error(monkeypatch):
    fake = FakeClient([SimpleNamespace(type="text", text="Here is the spec...")], stop_reason="end_turn")
    monkeypatch.setattr(gen.anthropic, "Anthropic", lambda: fake)
    with pytest.raises(ValueError, match="submit_spec"):
        gen.generate(PROBLEM)


def test_literal_backslash_n_in_captions_becomes_newline(monkeypatch):
    spec = yaml.safe_load(store.spec_path("two-sum").read_text())
    spec["statement"] = "Find two numbers\\nthat add up."
    spec["challenge"] = "Pause.\\nOne pass?"
    code = spec["approaches"][0]["code"]
    fake = FakeClient([SimpleNamespace(type="tool_use", name="submit_spec", input=spec)])
    monkeypatch.setattr(gen.anthropic, "Anthropic", lambda: fake)
    out = gen.generate(PROBLEM)
    assert out.statement == "Find two numbers\nthat add up."
    assert out.challenge == "Pause.\nOne pass?"
    assert out.approaches[0].code == code  # code is left alone
