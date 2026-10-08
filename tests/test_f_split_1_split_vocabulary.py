"""test_f_split_1_split_vocabulary.py — F-SPLIT-1 regression.

The AblationRunner previously resolved its scenario split with
``split_map.get(self.split, ScenarioSplit.DEV)``. Any label outside the
canonical vocabulary therefore produced a DEV scenario instead of an error —
a fail-open default in the path that is supposed to guarantee split integrity.
The most consequential instance was ``split="validation"``: the canonical
value is ``"val"``, so validation-intent callers silently ran DEV.

These tests pin the corrected contract:

  * the accepted vocabulary is exactly ScenarioSplit's own values, derived
    from the enum rather than duplicated;
  * every unrecognised value fails CLOSED at construction;
  * the three valid values keep byte-identical run_id behaviour;
  * no invalid input can ever yield a DEV scenario or a ``_dev`` run_id.

Deterministic and hermetic: fixed seeds, no network, no LLM dispatch
(generation is exercised only through a recording stub template).

Run: python -m pytest tests/test_f_split_1_split_vocabulary.py -q
"""

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from arena.ablation import ABLATION_PRESETS
from arena.ablation_runner import (
    AblationRunner,
    InvalidScenarioSplit,
    _resolve_scenario_split,
)
from arena.templates.base import ScenarioSplit


class _RecordingTemplate:
    """Stub template that records the split it was handed.

    AblationRunner needs family_id at init and generate() only when the
    scenario is actually built, so this stays cheap and side-effect free.
    """

    family_id = "T9_SEMANTIC_AMBIGUITY"
    schema_version = 2

    def __init__(self):
        self.calls = []

    def generate(self, seed=0, split=None, scenario_id_override=None):
        self.calls.append({"seed": seed, "split": split})
        return object()


def _make_runner(split, seed=42, template=None):
    return AblationRunner(
        template=template or _RecordingTemplate(),
        config=ABLATION_PRESETS["FULL_RAPHAEL"],
        seed=seed,
        split=split,
    )


# The canonical vocabulary is closed and case-sensitive.
VALID_SPLITS = ("dev", "val", "holdout")

# The regression corpus: every one of these previously became DEV.
INVALID_SPLITS = [
    "validation",       # the historical defect: intended val, became dev
    "DEV",              # wrong case
    "Validation",       # wrong case
    "VAL",              # wrong case
    "Holdout",          # wrong case
    "",                 # empty string
    " ",                # whitespace only
    "holdout ",         # trailing space
    " dev",             # leading space
    "dev ",             # trailing space
    "\tdev",            # leading tab
    "val\n",            # trailing newline
    "dev\nholdout",     # injection-ish multi-token
    "holdout\0",        # NUL suffix
    "none",             # near-miss on None
    "train",            # common ML vocabulary, not a scenario split
    "test",             # ditto
    "HOLDOUT",          # shouty
    "nonexistent",      # unknown
]


# --------------------------------------------------------------------------
# A–F: malformed / forged input must be REFUSED
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "bad",
    [
        pytest.param("validation", id="A-validation"),
        pytest.param("DEV", id="B-uppercase-dev"),
        pytest.param("Validation", id="C-mixedcase-validation"),
        pytest.param("", id="D-empty-string"),
        pytest.param(None, id="E-none"),
        pytest.param("holdout ", id="F-trailing-space-holdout"),
    ],
)
def test_named_invalid_split_fails_closed_at_construction(bad):
    """The six explicitly required refusals, named per the F-SPLIT-1 contract."""
    with pytest.raises(InvalidScenarioSplit):
        _make_runner(bad)


@pytest.mark.parametrize("bad", INVALID_SPLITS, ids=range(len(INVALID_SPLITS)))
def test_invalid_split_fails_closed_full_corpus(bad):
    """Every malformed/forged label is refused, not coerced."""
    with pytest.raises(InvalidScenarioSplit):
        _make_runner(bad)


@pytest.mark.parametrize("bad", [None, 0, 1, True, [], {}, (), b"dev", object()])
def test_non_string_split_fails_closed(bad):
    """Non-string and non-enum inputs are refused rather than defaulted."""
    with pytest.raises(InvalidScenarioSplit):
        _make_runner(bad)


def test_invalid_split_error_is_a_value_error():
    """The refusal is catchable as ValueError, so existing error handling holds."""
    with pytest.raises(ValueError):
        _make_runner("validation")


def test_invalid_split_error_names_the_accepted_vocabulary():
    """The message must be actionable: it lists the accepted values."""
    with pytest.raises(InvalidScenarioSplit) as exc:
        _make_runner("validation")
    message = str(exc.value)
    for accepted in VALID_SPLITS:
        assert repr(accepted) in message or accepted in message
    # The classic trap is called out explicitly.
    assert "not 'validation'" in message


def test_rejection_happens_before_any_runner_state_exists():
    """Construction fails before run_id / recorder / service are built.

    Guards the ordering requirement: no partially-initialised runner, and no
    evidence directory named after an invalid split.
    """
    with pytest.raises(InvalidScenarioSplit):
        _make_runner("validation")
    # Nothing was constructed, so no object escaped with a DEV identity.
    assert not list(Path(_REPO_ROOT / "src" / "arena" / "results").glob("abl_*_validation*"))


# --------------------------------------------------------------------------
# G–I: valid input must still PASS (the positive control)
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "value,expected_member",
    [
        pytest.param("dev", ScenarioSplit.DEV, id="G-dev"),
        pytest.param("val", ScenarioSplit.VALIDATION, id="H-val"),
        pytest.param("holdout", ScenarioSplit.HOLDOUT, id="I-holdout"),
    ],
)
def test_valid_split_resolves_to_expected_member(value, expected_member):
    runner = _make_runner(value)
    assert runner.scenario_split is expected_member
    assert runner.split == value


def test_valid_run_ids_are_byte_identical_to_previous_behaviour():
    """Valid run_id values are unchanged by the correction.

    These are the exact strings the pre-correction code produced, because the
    canonical member value equals the label the caller passed.
    """
    assert _make_runner("dev", seed=7).run_id == (
        "abl_FULL_RAPHAEL_T9_SEMANTIC_AMBIGUITY_s0007_dev"
    )
    assert _make_runner("val", seed=7).run_id == (
        "abl_FULL_RAPHAEL_T9_SEMANTIC_AMBIGUITY_s0007_val"
    )
    assert _make_runner("holdout", seed=7).run_id == (
        "abl_FULL_RAPHAEL_T9_SEMANTIC_AMBIGUITY_s0007_holdout"
    )


def test_valid_run_ids_are_deterministic_across_instances():
    """Same logical cell -> same run_id, as before."""
    assert _make_runner("dev", seed=7).run_id == _make_runner("dev", seed=7).run_id
    assert _make_runner("val", seed=3).run_id == _make_runner("val", seed=3).run_id


def test_valid_splits_generate_their_own_scenario_split():
    """A built scenario receives the resolved member, never a substitute."""
    for value, expected in (
        ("dev", ScenarioSplit.DEV),
        ("val", ScenarioSplit.VALIDATION),
        ("holdout", ScenarioSplit.HOLDOUT),
    ):
        template = _RecordingTemplate()
        runner = _make_runner(value, template=template)
        runner._build_scenario()
        assert template.calls == [{"seed": 42, "split": expected}]


def test_default_split_is_dev():
    """The documented default is unchanged: an omitted split is dev."""
    import inspect

    from arena.ablation_runner import AblationRunner as _AR

    signature = inspect.signature(_AR.__init__)
    assert signature.parameters["split"].default == "dev"
    # And an omitted split behaves as dev, not as an error.
    assert _AR(
        template=_RecordingTemplate(),
        config=ABLATION_PRESETS["FULL_RAPHAEL"],
        seed=42,
    ).scenario_split is ScenarioSplit.DEV


# --------------------------------------------------------------------------
# J: the adversarial control — no invalid input may become DEV
# --------------------------------------------------------------------------

@pytest.mark.parametrize("bad", INVALID_SPLITS + [None, 0, True, [], {}])
def test_no_invalid_input_can_yield_a_dev_identity(bad):
    """An invalid split must never produce a DEV scenario or DEV run_id.

    This is the control that catches a plausible-but-wrong fix: one that
    changes the exception type while still defaulting to dev.
    """
    # No runner object can be produced at all...
    with pytest.raises(InvalidScenarioSplit):
        runner = _make_runner(bad)
        assert runner.run_id.endswith("_dev") is False, "invalid split yielded DEV identity"

    # ...and the resolver itself never returns DEV for invalid input.
    with pytest.raises(InvalidScenarioSplit):
        assert _resolve_scenario_split(bad) is not ScenarioSplit.DEV


@pytest.mark.parametrize("value,expected_value", list(zip(VALID_SPLITS, VALID_SPLITS)))
def test_resolver_accepts_exactly_the_three_canonical_values(value, expected_value):
    assert _resolve_scenario_split(value).value == expected_value


def test_resolver_passes_through_enum_members():
    """An already-resolved ScenarioSplit is accepted unchanged."""
    for member in ScenarioSplit:
        assert _resolve_scenario_split(member) is member


def test_accepted_vocabulary_matches_the_enum_exactly():
    """The closed vocabulary is derived from ScenarioSplit, not hand-listed."""
    assert sorted(member.value for member in ScenarioSplit) == sorted(VALID_SPLITS)


def test_non_enum_looking_string_is_rejected_even_if_close_to_a_member():
    """Near-miss spellings are refused; there is no normalisation or aliasing."""
    for near in ("devs", "vali", "hold", "holdout_", "_dev", "dev\t"):
        with pytest.raises(InvalidScenarioSplit):
            _resolve_scenario_split(near)