"""Spec: vaccine-records-extraction, the extraction contract and the prompt."""

from datetime import date

import pytest
from pydantic import ValidationError

from app.prompts.records import PROMPT_VERSION, USER_TEXT, build_messages
from app.records import CertificateExtraction
from app.structured import strict_json_schema

spec = pytest.mark.spec

RECORD = {
    "label": "Rabies (3 yr)",
    "vaccine": "rabies",
    "administered_on": "2026-04-01",
    "expires_on": "2029-04-01",
}
VALID = {
    "pet_name": "Biscuit",
    "records": [RECORD],
    "readable": True,
    "confidence": 0.9,
    "ambiguities": [],
}


@spec("vaccine-records-extraction", "Extraction returns validated records")
def test_valid_extraction_parses():
    extraction = CertificateExtraction.model_validate(VALID)

    [record] = extraction.records
    assert record.administered_on == date(2026, 4, 1)
    assert record.expires_on == date(2029, 4, 1)


@spec("vaccine-records-extraction", "Extraction returns validated records")
@pytest.mark.parametrize(
    "bad",
    [
        VALID | {"compliant": True},
        VALID | {"confidence": 1.5},
        VALID | {"records": [RECORD | {"lot_number": "X1"}]},
        VALID | {"records": [RECORD | {"administered_on": "04/01/2026"}]},
        VALID | {"records": [RECORD | {"vaccine": "lyme"}]},
    ],
    ids=["extra-top", "confidence", "extra-record", "us-date-format", "unknown-enum"],
)
def test_invalid_extractions_are_rejected(bad):
    with pytest.raises(ValidationError):
        CertificateExtraction.model_validate(bad)


@spec("vaccine-records-extraction", "Extraction returns validated records")
def test_missing_expiry_and_unmapped_vaccine_are_representable():
    record = RECORD | {"label": "Lyme", "vaccine": None, "expires_on": None}

    extraction = CertificateExtraction.model_validate(VALID | {"records": [record]})

    assert extraction.records[0].vaccine is None
    assert extraction.records[0].expires_on is None


@spec("vaccine-records-extraction", "Extraction returns validated records")
def test_strict_schema_covers_nested_records():
    schema = strict_json_schema(CertificateExtraction)
    item = schema["properties"]["records"]["items"]

    assert set(schema["required"]) == set(VALID)
    assert set(item["required"]) == set(RECORD)
    assert item["additionalProperties"] is False


@spec("vaccine-records-extraction", "Expiry dates are never inferred")
def test_prompt_forbids_inferring_expiry():
    system, _ = build_messages(b"img", "image/png", date(2027, 3, 3), "America/Chicago")

    assert "If the certificate does not print an expiry" in system["content"]
    assert "NEVER calculate or estimate an expiry" in system["content"]


def test_prompt_maps_aliases_and_carries_the_image():
    system, user = build_messages(b"\x89PNG", "image/png", date(2027, 3, 3), "America/Chicago")

    for alias in ("DA2PP", "kennel cough", "H3N2", "FeLV"):
        assert alias in system["content"]
    text, image = user["content"]
    assert text == {"type": "text", "text": USER_TEXT}
    assert image["image_url"]["url"].startswith("data:image/png;base64,")
    assert PROMPT_VERSION.startswith("records-v")
