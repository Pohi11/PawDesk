"""Spec: vaccine-records-extraction, the pipeline against scripted model answers."""

import base64
import json
from datetime import date

import httpx
import pytest
from sqlalchemy import select, text

from app.compliance import Outcome, VaccineStatus, check
from app.db import make_sessionmaker
from app.enums import SpanKind, Vaccine
from app.llm import RetryPolicy, make_client
from app.models import Span
from app.prompts.records import PROMPT_VERSION
from app.records import RecordsInvalidOutput, RecordsOutcome, run_records
from tests.test_llm import Script, fake_settings, ok

spec = pytest.mark.spec
TODAY = date(2027, 3, 3)
PNG = b"\x89PNG\r\n\x1a\n" + b"synthetic certificate pixels " * 200

RABIES = {
    "label": "Rabies (3 yr)",
    "vaccine": "rabies",
    "administered_on": "2026-04-01",
    "expires_on": "2029-04-01",
}
DHPP = {
    "label": "DA2PP",
    "vaccine": "dhpp",
    "administered_on": "2026-04-01",
    "expires_on": "2027-04-01",
}
GOOD = {
    "pet_name": "Biscuit",
    "records": [RABIES, DHPP],
    "readable": True,
    "confidence": 0.9,
    "ambiguities": [],
}


def answer(**changes):
    return ok(text=json.dumps(GOOD | changes))


def raw(text_):
    return ok(text=text_)


async def _noop():
    return None


@pytest.fixture
def records(tracer, engine):
    async def run(*steps, image=PNG, booked_pet="Biscuit"):
        script = Script(*steps)
        settings = fake_settings()
        client = make_client(settings, transport=httpx.MockTransport(script))
        async with tracer.start_trace("records test") as trace_id:
            try:
                outcome = await run_records(
                    image,
                    booked_pet=booked_pet,
                    today=TODAY,
                    timezone="America/Chicago",
                    client=client,
                    settings=settings,
                    policy=RetryPolicy(sleep=lambda s: _noop()),
                )
            except RecordsInvalidOutput as exc:
                outcome = exc
        async with make_sessionmaker(engine)() as s:
            spans = list(await s.scalars(select(Span).where(Span.trace_id == trace_id)))
        return outcome, script, spans

    return run


# --- Extraction returns validated records ---------------------------------------------


@spec("vaccine-records-extraction", "Extraction returns validated records")
async def test_readable_certificate(records):
    result, script, _ = await records(answer())

    assert [(r.label, r.vaccine) for r in result.extraction.records] == [
        ("Rabies (3 yr)", Vaccine.RABIES),
        ("DA2PP", Vaccine.DHPP),
    ]
    assert len(result.evidence) == 2
    assert len(script.requests) == 1


@spec("vaccine-records-extraction", "Extraction returns validated records")
async def test_invalid_output_repaired_once(records):
    result, script, _ = await records(raw("I see a rabies shot."), answer())

    assert len(result.evidence) == 2
    assert len(script.requests) == 2


@spec("vaccine-records-extraction", "Extraction returns validated records")
async def test_invalid_twice(records):
    result, script, _ = await records(answer(compliant=True), answer(compliant=True))

    assert isinstance(result, RecordsInvalidOutput)
    assert len(script.requests) == 2


# --- Records feed compliance unchanged ------------------------------------------------


@spec("vaccine-records-extraction", "Records feed compliance unchanged")
async def test_records_drive_compliance(records):
    rabies_only = {
        "label": "Rabies",
        "vaccine": "rabies",
        "administered_on": "2026-04-01",
        "expires_on": "2027-04-01",
    }
    result, _, _ = await records(answer(records=[rabies_only]))

    [evidence] = result.evidence
    assert (evidence.administered_on, evidence.expires_on) == (date(2026, 4, 1), date(2027, 4, 1))
    stay = check({Vaccine.RABIES}, result.evidence, date(2027, 3, 10), date(2027, 3, 14))
    assert stay.outcome == Outcome.COMPLIANT


# --- Expiry dates are never inferred --------------------------------------------------


@spec("vaccine-records-extraction", "Expiry dates are never inferred")
async def test_missing_expiry_stays_missing_and_compliance_asks_a_person(records):
    fvrcp = {
        "label": "FVRCP",
        "vaccine": "fvrcp",
        "administered_on": "2026-05-01",
        "expires_on": None,
    }
    result, _, _ = await records(answer(records=[fvrcp]))

    [evidence] = result.evidence
    assert evidence.expires_on is None
    stay = check({Vaccine.FVRCP}, result.evidence, date(2027, 3, 10), date(2027, 3, 14))
    assert stay.checks[0].status == VaccineStatus.UNKNOWN_EXPIRY


@spec("vaccine-records-extraction", "Expiry dates are never inferred")
async def test_request_tells_the_model_never_to_infer(records):
    _, script, _ = await records(answer())

    system = json.loads(script.requests[0].content)["messages"][0]["content"]
    assert "NEVER calculate or estimate an expiry" in system


# --- Only acceptable images reach the model -------------------------------------------


@spec("vaccine-records-extraction", "Only acceptable images reach the model")
async def test_oversized_image(records):
    result, script, _ = await records(
        answer(), image=b"\x89PNG\r\n\x1a\n" + b"0" * (6 * 1024 * 1024)
    )

    assert script.requests == []
    assert result.outcome == RecordsOutcome.NEEDS_REVIEW


@spec("vaccine-records-extraction", "Only acceptable images reach the model")
@pytest.mark.parametrize(
    "data", [b"%PDF-1.7\n...", b"GIF89a....", b"just text"], ids=["pdf", "gif", "text"]
)
async def test_unsupported_type(records, data):
    result, script, _ = await records(answer(), image=data)

    assert script.requests == []
    assert result.outcome == RecordsOutcome.NEEDS_REVIEW
    assert "unsupported file type" in result.issues[0]


@spec("vaccine-records-extraction", "Only acceptable images reach the model")
@pytest.mark.parametrize(
    "data",
    [b"\xff\xd8\xff\xe0" + b"jpeg" * 50, b"RIFF\x00\x00\x00\x00WEBPVP8 " + b"w" * 50],
    ids=["jpeg", "webp"],
)
async def test_jpeg_and_webp_are_accepted(records, data):
    result, script, _ = await records(answer(), image=data)

    assert len(script.requests) == 1
    assert result.outcome == RecordsOutcome.CLEAR


# --- Extracted records are checked in code --------------------------------------------


@spec("vaccine-records-extraction", "Extracted records are checked in code")
@pytest.mark.parametrize(
    ("record", "issue"),
    [
        (RABIES | {"administered_on": "2027-05-01", "expires_on": "2030-05-01"}, "is after today"),
        (
            RABIES | {"administered_on": "2026-05-01", "expires_on": "2026-04-01"},
            "before the date given",
        ),
        (
            {
                "label": "Lyme",
                "vaccine": None,
                "administered_on": "2026-05-01",
                "expires_on": "2027-05-01",
            },
            "not a known vaccine",
        ),
    ],
    ids=["future-given", "expiry-before-given", "unknown-label"],
)
async def test_record_issues(records, record, issue):
    result, _, _ = await records(answer(records=[record]))

    assert any(issue in i for i in result.issues), result.issues
    assert result.outcome == RecordsOutcome.NEEDS_REVIEW


@spec("vaccine-records-extraction", "Extracted records are checked in code")
async def test_unknown_label_is_not_passed_to_compliance(records):
    lyme = {
        "label": "Lyme",
        "vaccine": None,
        "administered_on": "2026-05-01",
        "expires_on": "2027-05-01",
    }
    result, _, _ = await records(answer(records=[RABIES, lyme]))

    assert [e.vaccine for e in result.evidence] == [Vaccine.RABIES]


@spec("vaccine-records-extraction", "Extracted records are checked in code")
async def test_certificate_for_another_pet(records):
    result, _, _ = await records(answer(pet_name="Max"))

    assert "certificate names 'Max', booking is for 'Biscuit'" in result.issues


@spec("vaccine-records-extraction", "Extracted records are checked in code")
async def test_matching_pet_name(records):
    result, _, _ = await records(answer(pet_name="BISCUIT "))

    assert not any("certificate names" in i for i in result.issues)


@spec("vaccine-records-extraction", "Extracted records are checked in code")
async def test_no_records_found(records):
    result, _, _ = await records(answer(records=[]))

    assert "no vaccination records found" in result.issues


# --- Doubtful extractions go to a person ----------------------------------------------


@spec("vaccine-records-extraction", "Doubtful extractions go to a person")
@pytest.mark.parametrize(
    ("changes", "issue"),
    [
        ({"readable": False}, "image not readable"),
        ({"confidence": 0.5}, "low confidence (0.50)"),
        ({"ambiguities": ["rabies date smudged"]}, "ambiguous: rabies date smudged"),
    ],
    ids=["unreadable", "low-confidence", "ambiguity"],
)
async def test_doubt_goes_to_review(records, changes, issue):
    result, _, _ = await records(answer(**changes))

    assert issue in result.issues
    assert result.outcome == RecordsOutcome.NEEDS_REVIEW


@spec("vaccine-records-extraction", "Doubtful extractions go to a person")
async def test_clean_extraction(records):
    result, _, _ = await records(answer())

    assert result.issues == ()
    assert result.outcome == RecordsOutcome.CLEAR


# --- Extraction is traced without storing the image -----------------------------------


@spec("vaccine-records-extraction", "Extraction is traced without storing the image")
async def test_traced_without_the_image(records, engine):
    _, _, spans = await records(answer())

    [root] = [s for s in spans if s.name == "records"]
    [child] = [s for s in spans if s.parent_span_id == root.id]
    assert (root.kind, child.kind, child.name) == (SpanKind.CODE, SpanKind.LLM, "records.extract")
    assert root.attributes["prompt_version"] == PROMPT_VERSION
    assert len(root.attributes["image_sha256"]) == 64
    assert root.output["outcome"] == "clear"
    image_b64 = base64.b64encode(PNG).decode()
    async with make_sessionmaker(engine)() as s:
        stored = await s.scalar(
            text("SELECT string_agg(row_to_json(s)::text, '') FROM spans s WHERE trace_id = :t"),
            {"t": root.trace_id},
        )
    assert image_b64[:200] not in stored
    assert "[image sha256=" in stored
