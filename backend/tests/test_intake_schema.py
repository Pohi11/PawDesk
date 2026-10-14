"""Spec: booking-intake, the intent contract and the provider schema derived from it."""

from datetime import date

import pytest
from pydantic import ValidationError

from app.enums import Service
from app.intake import BookingIntent, response_format, strict_json_schema

spec = pytest.mark.spec

VALID = {
    "pet_name": "Biscuit",
    "service": "boarding",
    "start_date": "2027-03-06",
    "end_date": "2027-03-09",
    "special_notes": "Shy at night.",
    "confidence": 0.92,
    "ambiguities": [],
}
FIELDS = set(VALID)


@spec("booking-intake", "Intake produces a validated intent")
def test_well_formed_output_parses():
    intent = BookingIntent.model_validate_json(
        '{"pet_name": "Biscuit", "service": "boarding", "start_date": "2027-03-06",'
        ' "end_date": "2027-03-09", "special_notes": "", "confidence": 0.9, "ambiguities": []}'
    )

    assert (intent.pet_name, intent.service) == ("Biscuit", Service.BOARDING)
    assert (intent.start_date, intent.end_date) == (date(2027, 3, 6), date(2027, 3, 9))


@spec("booking-intake", "Intake produces a validated intent")
def test_nulls_are_allowed_where_the_message_says_nothing():
    intent = BookingIntent.model_validate(
        VALID | {"pet_name": None, "service": None, "start_date": None, "end_date": None}
    )

    assert intent.pet_name is None and intent.start_date is None


@spec("booking-intake", "Intake produces a validated intent")
def test_unknown_extra_field_is_rejected():
    with pytest.raises(ValidationError, match="approved"):
        BookingIntent.model_validate(VALID | {"approved": True})


@spec("booking-intake", "Intake produces a validated intent")
@pytest.mark.parametrize("confidence", [1.7, -0.1])
def test_out_of_range_confidence_is_rejected(confidence):
    with pytest.raises(ValidationError, match="confidence"):
        BookingIntent.model_validate(VALID | {"confidence": confidence})


@spec("booking-intake", "Intake produces a validated intent")
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("service", "spa_day"),
        ("start_date", "2027-02-30"),
        ("special_notes", "x" * 501),
        ("ambiguities", ["fine"] * 11),
    ],
)
def test_invalid_values_are_rejected(field, value):
    with pytest.raises(ValidationError):
        BookingIntent.model_validate(VALID | {field: value})


@spec("booking-intake", "Intake produces a validated intent")
def test_every_field_is_required():
    for missing in FIELDS:
        with pytest.raises(ValidationError):
            BookingIntent.model_validate({k: v for k, v in VALID.items() if k != missing})


@spec("booking-intake", "Structured output is requested from the provider")
def test_strict_schema_requires_every_field_and_forbids_extras():
    schema = strict_json_schema(BookingIntent)

    assert schema["type"] == "object"
    assert set(schema["properties"]) == FIELDS
    assert set(schema["required"]) == FIELDS
    assert schema["additionalProperties"] is False


@spec("booking-intake", "Structured output is requested from the provider")
def test_strict_schema_uses_only_portable_keywords():
    text = str(strict_json_schema(BookingIntent))

    for keyword in ("'title'", "'default'", "'$ref'", "'$defs'", "'format'", "'maximum'"):
        assert keyword not in text
    assert "description" not in strict_json_schema(BookingIntent)  # no developer docstring


@spec("booking-intake", "Structured output is requested from the provider")
def test_service_enum_is_inlined_and_nullable():
    service = strict_json_schema(BookingIntent)["properties"]["service"]

    options = service["anyOf"]
    assert {"type": "null"} in options
    enum = next(o for o in options if "enum" in o)
    assert set(enum["enum"]) == {"boarding", "daycare", "grooming"}


@spec("booking-intake", "Structured output is requested from the provider")
def test_response_format_wraps_the_schema_in_strict_mode():
    rf = response_format()

    assert rf["type"] == "json_schema"
    assert rf["json_schema"]["strict"] is True
    assert rf["json_schema"]["schema"] == strict_json_schema(BookingIntent)
