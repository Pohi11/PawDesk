"""The lifecycle the Architecture page draws matches the backend (spec: run-dashboard). The
page reads frontend/content/architecture.json; this test compares it with the lifecycle
rules and the orchestrator's step map."""

import json
from pathlib import Path

import pytest

from app.lifecycle import ALLOWED, CAN_FAIL, Actor, State
from app.orchestrator import STEPS

spec = pytest.mark.spec
REQUIREMENT = "The architecture page's lifecycle matches the backend"
DATA = Path(__file__).resolve().parents[2] / "frontend" / "content" / "architecture.json"


@pytest.fixture(scope="module")
def page() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


@spec("run-dashboard", REQUIREMENT)
def test_transitions_match_the_lifecycle_rules(page):
    shown = [(State(t["from"]), State(t["to"]), Actor(t["actor"])) for t in page["transitions"]]
    # FAILED edges are drawn as notches on the failable states, not as arrows.
    drawn_rules = {rule for rule in ALLOWED if rule[1] != State.FAILED}
    assert len(shown) == len(set(shown))
    assert set(shown) == drawn_rules


@spec("run-dashboard", REQUIREMENT)
def test_failable_states_match(page):
    assert {State(s) for s in page["can_fail"]} == CAN_FAIL
    assert {rule[0] for rule in ALLOWED if rule[1] == State.FAILED} == CAN_FAIL


@spec("run-dashboard", REQUIREMENT)
def test_step_table_matches_the_orchestrator(page):
    shown = {State(s["state"]): s["step"] for s in page["steps"]}
    assert shown == {state: fn.__name__ for state, fn in STEPS.items()}
