"""Spec: certificate-evaluation, repeated reads of the sample cards (scoring is pure)."""

from datetime import UTC, datetime

import pytest

from app.prompts.records import PROMPT_VERSION
from scripts.eval_sample_cards import (
    build_report,
    printed_records,
    sample_stay,
    score_read,
    totals,
)

spec = pytest.mark.spec
REQ = "Sample cards are read repeatedly to measure misreads"


def read(records, outcome="clear"):
    return {
        "records": [r | {"label": r["vaccine"]} for r in records],
        "outcome": outcome,
        "issues": [],
    }


def shifted(records, vaccine, **dates):
    return [r | dates if r["vaccine"] == vaccine else r for r in records]


@spec("certificate-evaluation", REQ)
def test_a_shifted_year_is_a_misread():
    printed = printed_records("clean")
    got = shifted(printed, "bordetella", administered_on="2024-10-12")
    assert score_read(printed, read(got), sample_stay("clean"))["misread"]


@spec("certificate-evaluation", REQ)
def test_exact_read_is_neither_misread_nor_flip():
    printed = printed_records("clean")
    score = score_read(printed, read(printed), sample_stay("clean"))
    assert not score["misread"] and not score["flip"] and not score["silent_flip"]


@spec("certificate-evaluation", REQ)
def test_a_misread_that_changes_the_decision():
    # The hosted run's read: Bordetella expiring 2025-11-03 doesn't cover Mar 24-27, 2027.
    printed = printed_records("clean")
    got = shifted(printed, "bordetella", administered_on="2024-10-12", expires_on="2025-11-03")
    score = score_read(printed, read(got), sample_stay("clean"))
    assert score["misread"] and score["flip"]


@spec("certificate-evaluation", REQ)
def test_a_silent_flip():
    printed = printed_records("clean")
    got = shifted(printed, "bordetella", expires_on="2025-11-03")
    stay = sample_stay("clean")
    assert score_read(printed, read(got, "clear"), stay)["silent_flip"]
    assert not score_read(printed, read(got, "needs_review"), stay)["silent_flip"]


@spec("certificate-evaluation", REQ)
def test_a_failed_read_is_counted_apart():
    printed = printed_records("clean")
    score = score_read(printed, read([], "error"), sample_stay("clean"))
    assert totals([score]) == {
        "reads": 1,
        "failed": 1,
        "misreads": 0,
        "decision_flips": 0,
        "silent_flips": 0,
    }


@spec("certificate-evaluation", REQ)
def test_report_names_what_it_measured():
    printed = printed_records("clean")
    row = {"read": read(printed), "score": score_read(printed, read(printed), sample_stay("clean"))}
    report = build_report(
        {"clean": [row, row]},
        reads_per_card=2,
        model="some/model",
        started=datetime.now(UTC),
        trace_id="t",
        cost="0.01",
    )
    assert report["prompt_version"] == PROMPT_VERSION
    assert report["model"] == "some/model"
    assert report["reads_per_card"] == 2
    assert report["total_cost_usd"] == "0.01"
    assert report["summary"]["by_card"]["clean"]["reads"] == 2
