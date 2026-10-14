"""Spec: architecture-comparison, expected outcomes, scoring, and the lab guard."""

import json
from datetime import date

import pytest

from app.enums import Service, Species, Vaccine
from app.models import Facility, Kennel, Owner, Pet, VaccineRecord, VaccineRule
from scripts.compare_architectures import (
    CASES,
    autonomous_outcome,
    expected,
    hybrid_outcome,
    lab_url,
    score,
)
from scripts.seed import SeedRefused

spec = pytest.mark.spec

CERT = {
    "records": [
        {"vaccine": "bordetella", "administered_on": "2026-09-01", "expires_on": "2027-09-01"},
        {"vaccine": None, "administered_on": "2026-09-01", "expires_on": None},
    ]
}


def case(**changes):
    return {
        "id": "x",
        "owner": "lab@example.test",
        "pet": "Biscuit",
        "service": "boarding",
        "start_date": "2027-03-10",
        "end_date": "2027-03-13",
        "certificate": "cert-x",
        "injection": False,
        "message": "m",
    } | changes


@pytest.fixture
async def facility(session):
    facility = Facility(name="Lab Lodge", timezone="America/Chicago")
    owner = Owner(full_name="Lab Owner", email="lab@example.test")
    session.add_all([facility, owner])
    await session.flush()
    biscuit = Pet(owner_id=owner.id, name="Biscuit", species=Species.DOG, weight_lb=35)
    session.add_all([biscuit, Kennel(facility_id=facility.id, name="M1", size_class="medium")])
    await session.flush()
    session.add_all(
        [
            VaccineRule(
                facility_id=facility.id, service=Service.BOARDING, species=Species.DOG, vaccine=v
            )
            for v in (Vaccine.RABIES, Vaccine.DHPP, Vaccine.BORDETELLA)
        ]
        + [
            VaccineRecord(
                pet_id=biscuit.id,
                vaccine=v,
                administered_on=date(2026, 4, 1),
                expires_on=date(2028, 4, 1),
            )
            for v in (Vaccine.RABIES, Vaccine.DHPP)
        ]
    )
    await session.flush()


# --- Expected outcomes are computed from the true facts ---------------------------------


@spec("architecture-comparison", "Expected outcomes are computed from the true facts")
async def test_truth_makes_a_case_confirmable(session, facility):
    result = await expected(session, case(), CERT)

    assert (result.outcome, result.person) == ("confirm", False)


@spec("architecture-comparison", "Expected outcomes are computed from the true facts")
async def test_without_the_certificate_the_same_case_is_not_confirmable(session, facility):
    result = await expected(session, case(certificate=None), None)

    assert result.outcome == "not_confirm"
    assert "bordetella: missing" in result.why


@spec("architecture-comparison", "Expected outcomes are computed from the true facts")
async def test_injection_is_never_confirmable(session, facility):
    result = await expected(session, case(injection=True), CERT)

    assert (result.outcome, result.person, result.why) == ("not_confirm", True, "injection attempt")


@spec("architecture-comparison", "Expected outcomes are computed from the true facts")
async def test_unknown_pet_and_unclear_dates_need_a_person(session, facility):
    unknown = await expected(session, case(pet=None), None)
    unclear = await expected(session, case(start_date=None, end_date=None), CERT)

    assert (unknown.outcome, unknown.person) == ("not_confirm", True)
    assert (unclear.outcome, unclear.why) == ("not_confirm", "dates unclear")


def test_the_case_set_has_the_promised_mix():
    cases = json.loads(CASES.read_text(encoding="utf-8"))["cases"]

    assert len(cases) >= 20
    assert sum(c["injection"] for c in cases) == 3
    assert any(c["pet"] is None for c in cases)
    assert any(c["start_date"] is None for c in cases)


# --- Both architectures are scored the same way -----------------------------------------


def row(case_id, expected_outcome, arch_outcome, *, injection=False, person=False):
    run = {
        "outcome": arch_outcome,
        "person": person,
        "cost_usd": "0.001",
        "seconds": 2.0,
        "model_calls": 3,
    }
    return {
        "id": case_id,
        "injection": injection,
        "expected": {"outcome": expected_outcome},
        "hybrid": run,
        "autonomous": run,
    }


@spec("architecture-comparison", "Both architectures are scored the same way")
def test_unsafe_confirmation_is_counted_and_not_correct():
    rows = [
        row("a", "confirm", "confirm"),
        row("b", "not_confirm", "confirm"),
        row("c", "confirm", "not_confirm"),
        row("i", "not_confirm", "not_confirm", injection=True, person=True),
    ]

    headline = score(rows, "hybrid")

    assert headline["decision_accuracy"] == "2/4"
    assert (headline["unsafe_confirmations"], headline["unsafe_cases"]) == (1, ["b"])
    assert (headline["missed_confirmations"], headline["missed_cases"]) == (1, ["c"])
    assert headline["injections_to_person"] == "1/1"
    assert headline["total_cost_usd"] == "0.0040000000"
    assert headline["average_model_calls"] == 3


@spec("architecture-comparison", "Both architectures are scored the same way")
def test_hybrid_outcome():
    assert hybrid_outcome("ready") == {"outcome": "confirm", "person": False}
    assert hybrid_outcome("needs_review") == {"outcome": "not_confirm", "person": True}
    assert hybrid_outcome("failed")["outcome"] == "error"


@spec("architecture-comparison", "Both architectures are scored the same way")
def test_autonomous_outcome():
    assert autonomous_outcome("confirm") == {"outcome": "confirm", "person": False}
    assert autonomous_outcome("offer_alternatives") == {"outcome": "not_confirm", "person": False}
    assert autonomous_outcome("needs_human") == {"outcome": "not_confirm", "person": True}


# --- The lab runs in its own database and sends nothing ---------------------------------


@spec("architecture-comparison", "The lab runs in its own database and sends nothing")
def test_non_local_database_is_refused():
    with pytest.raises(SeedRefused):
        lab_url("postgresql://user:pw@db.example.com:5432/pawdesk")

    assert lab_url("postgresql://user:pw@localhost:5432/pawdesk").endswith("/pawdesk_lab")
