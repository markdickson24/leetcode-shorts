import typing

import pytest

from shorts import store
from shorts.spec import TemplateName
from shorts.templates import TEMPLATES
from shorts.tts import speakable
from shorts.verify import VerificationError, verify


def test_template_registry_matches_schema():
    assert set(typing.get_args(TemplateName)) == set(TEMPLATES)


@pytest.mark.parametrize("slug", [p.stem for p in store.SPECS.glob("*.yaml")])
def test_saved_specs_verify(slug):
    traces = verify(store.load_spec(slug))
    assert all(traces)


def test_wrong_solution_is_caught():
    spec = store.load_spec("two-sum")
    spec.approaches[1].code = spec.approaches[1].code.replace("return [seen[need], i]", "return [i, i]")
    with pytest.raises(VerificationError, match="expected"):
        verify(spec)


def test_bad_highlight_is_caught():
    spec = store.load_spec("two-sum")
    spec.approaches[0].highlights["check"] = 99
    with pytest.raises(VerificationError, match="outside"):
        verify(spec)


def test_speakable():
    assert speakable("That's O(n²).\nOne pass → done") == "That's O of n squared. One pass to done"
