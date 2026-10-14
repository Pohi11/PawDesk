"""Spec: certificate-evaluation, scoring (pure) and a scripted end-to-end run."""

import json

import httpx
import pytest

from app.llm import RetryPolicy, make_client
from scripts.eval_records import (
    compliance_outcome,
    evaluate,
    load_truth,
    match_records,
    score_certificate,
    summarize,
)
from tests.test_llm import Script, fake_settings, ok

spec = pytest.mark.spec
STAY = {"service": "boarding", "start": "2027-03-10", "end": "2027-03-13"}


def rec(vaccine, given="2026-04-01", expires="2027-04-01", label=None):
    return {
        "label": label or vaccine,
        "vaccine": vaccine,
        "administered_on": given,
        "expires_on": expires,
    }


def cert(records, species="dog", pet="Biscuit"):
    return {"id": "c", "species": species, "pet_name": pet, "records": records}


def actual(records, pet="Biscuit", outcome="clear"):
    return {"pet_name": pet, "records": records, "outcome": outcome, "issues": []}


@spec("certificate-evaluation", "Evaluation reports field accuracy and invented expiries")
def test_scoring_a_partly_wrong_extraction():
    truth = [rec("rabies"), rec("dhpp")]
    got = [rec("rabies", expires="2027-05-01"), rec("bordetella")]

    s = score_certificate(cert(truth), actual(got), STAY)

    assert (s["matched"], s["truth_records"]) == (1, 2)  # recall 1/2
    assert (s["matched"], s["extracted_records"]) == (1, 2)  # precision 1/2
    assert (s["expiry_correct"], s["matched"]) == (0, 1)
    assert s["given_correct"] == 1


@spec("certificate-evaluation", "Evaluation reports field accuracy and invented expiries")
def test_invented_expiry_is_counted():
    truth = [rec("rabies"), rec("fvrcp", expires=None)]
    got = [rec("rabies"), rec("fvrcp", expires="2029-04-01")]

    s = score_certificate(cert(truth, species="cat"), actual(got), STAY)

    assert s["invented_expiries"] == 1
    assert s["expiry_correct"] == 1  # rabies right; a correctly empty expiry also counts


@spec("certificate-evaluation", "Evaluation reports field accuracy and invented expiries")
def test_duplicate_vaccines_pair_by_best_date_match():
    truth = [rec("rabies", given="2024-01-01", expires="2025-01-01"), rec("rabies")]
    got = [rec("rabies"), rec("rabies", given="2024-01-01", expires="2025-01-01")]

    pairs = match_records(truth, got)

    assert all(a == b for a, b in pairs)


@spec("certificate-evaluation", "Evaluation reports decision agreement")
def test_error_that_changes_the_decision():
    expired = [rec("rabies"), rec("dhpp"), rec("bordetella", expires="2027-03-01")]
    misread = [rec("rabies"), rec("dhpp"), rec("bordetella", expires="2027-08-01")]

    s = score_certificate(cert(expired), actual(misread), STAY)

    assert compliance_outcome(expired, "dog", STAY) == "not_compliant"
    assert s["extracted_decision"] == "compliant"
    assert s["decision_agrees"] is False
    assert s["silent_disagreement"] is True  # wrong and nobody was asked to look


@spec("certificate-evaluation", "Evaluation reports decision agreement")
def test_disagreement_sent_to_review_is_not_silent():
    expired = [rec("rabies"), rec("dhpp"), rec("bordetella", expires="2027-03-01")]
    misread = [rec("rabies"), rec("dhpp"), rec("bordetella", expires="2027-08-01")]

    s = score_certificate(cert(expired), actual(misread, outcome="needs_review"), STAY)

    assert s["decision_agrees"] is False
    assert s["silent_disagreement"] is False


@spec("certificate-evaluation", "Evaluation reports field accuracy and invented expiries")
@spec("certificate-evaluation", "Evaluation reports decision agreement")
async def test_scripted_end_to_end_on_two_certificates(tracer):
    doc = load_truth()
    two = doc | {"certificates": doc["certificates"][:2]}
    # Certificate 1 read perfectly; certificate 2 read with every expiry missing.
    replies = []
    for i, c in enumerate(two["certificates"]):
        records = [r | ({"expires_on": None} if i == 1 else {}) for r in c["records"]]
        replies.append(
            {
                "pet_name": c["pet_name"],
                "records": records,
                "readable": True,
                "confidence": 0.95,
                "ambiguities": [],
            }
        )
    script = Script(*(ok(text=json.dumps(r)) for r in replies))
    settings = fake_settings()
    client = make_client(settings, transport=httpx.MockTransport(script))

    async with tracer.start_trace("records eval test"):
        scored = await evaluate(two, client=client, settings=settings, policy=RetryPolicy())
    summary = summarize(scored)

    first, second = (row["score"] for row in scored)
    assert first["expiry_correct"] == first["matched"] == first["truth_records"]
    assert first["decision_agrees"] is True
    assert second["expiry_correct"] == sum(
        r["expires_on"] is None for r in two["certificates"][1]["records"]
    )
    total = summary["total"]
    assert total["certificates"] == 2
    assert total["invented_expiries"] == 0
    assert set(summary["by_variant"]) == {c["variant"] for c in two["certificates"]}


@spec("certificate-evaluation", "Evaluation reports decision agreement")
async def test_failed_model_call_is_scored_as_error_not_a_crash(tracer):
    doc = load_truth()
    one = doc | {"certificates": doc["certificates"][:1]}
    script = Script(*(httpx.Response(503, json={"error": {"code": 503}}) for _ in range(3)))
    settings = fake_settings()
    client = make_client(settings, transport=httpx.MockTransport(script))

    async def no_wait():
        return None

    async with tracer.start_trace("records eval failure"):
        [row] = await evaluate(
            one, client=client, settings=settings, policy=RetryPolicy(sleep=lambda s: no_wait())
        )

    assert row["actual"]["outcome"] == "error"
    assert row["score"]["extracted_decision"] == "error"
    assert row["score"]["decision_agrees"] is False
    assert row["score"]["silent_disagreement"] is False  # a failure is visible, not silent
    assert summarize([row])["total"]["errors"] == 1


@spec("certificate-evaluation", "Benchmark versions are kept side by side")
def test_evaluation_defaults_to_v2_and_report_names_it():
    from datetime import UTC, datetime

    from scripts.eval_records import build_report

    doc = load_truth()
    report = build_report(doc, [], started=datetime.now(UTC), trace_id="t", cost=None)

    assert doc["version"] == "v2"
    assert report["benchmark"]["version"] == "v2"
    assert load_truth("v1")["version"] == "v1"
