"""The architecture comparison lab: PawDesk's hybrid workflow against a single autonomous
agent, on the same cases, in a separate lab database (spec: architecture-comparison).

Run from backend/ (real model calls, a few tenths of a dollar at most):
    uv run python -m scripts.compare_architectures

Expected outcomes are computed from each case's true facts with the deterministic checks,
not labeled by hand. The hybrid workflow is stopped after drafting, so nothing is sent.
"""

import statistics
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession

from app.capacity import find_kennel
from app.compliance import Outcome, VaccineEvidence, check, load_evidence, load_requirements
from app.enums import Service, Vaccine
from app.lifecycle import State
from app.models import Facility, Owner, Pet
from scripts.seed import ensure_local

EVALS = Path(__file__).resolve().parents[1] / "evals"
CASES = EVALS / "comparison_cases.json"
TRUTH = EVALS / "certificates" / "v2" / "truth.json"
LAB_DATABASE = "pawdesk_lab"


# --- Expected outcomes from the true facts (design D2) ---------------------------------


@dataclass(frozen=True)
class Expected:
    outcome: str  # confirm | not_confirm
    person: bool  # a hand-off to a person is required
    why: str


def truth_evidence(certificate: dict[str, Any] | None) -> list[VaccineEvidence]:
    if certificate is None:
        return []
    return [
        VaccineEvidence(
            Vaccine(r["vaccine"]),
            date.fromisoformat(r["administered_on"]),
            date.fromisoformat(r["expires_on"]) if r["expires_on"] else None,
        )
        for r in certificate["records"]
        if r["vaccine"]
    ]


async def expected(
    session: AsyncSession, case: dict[str, Any], certificate: dict[str, Any] | None
) -> Expected:
    """What a perfect reader would conclude with the facility's own rules."""
    if case["injection"]:
        return Expected("not_confirm", True, "injection attempt")
    if not case["pet"]:
        return Expected("not_confirm", True, "pet not on file")
    if not case["start_date"]:
        return Expected("not_confirm", True, "dates unclear")

    owner = await session.scalar(select(Owner).where(Owner.email == case["owner"]))
    pet = await session.scalar(select(Pet).where(Pet.owner_id == owner.id, Pet.name == case["pet"]))
    facility_id = await session.scalar(select(Facility.id).limit(1))
    service = Service(case["service"])
    start, end = date.fromisoformat(case["start_date"]), date.fromisoformat(case["end_date"])

    required = await load_requirements(session, facility_id, service, pet.species)
    evidence = await load_evidence(session, pet.id) + truth_evidence(certificate)
    compliance = check(required, evidence, start, end)
    if compliance.outcome != Outcome.COMPLIANT:
        failing = [f"{c.vaccine}: {c.status}" for c in compliance.checks if c.status != "ok"]
        return Expected(
            "not_confirm", False, f"compliance {compliance.outcome} ({', '.join(failing)})"
        )
    if (
        service == Service.BOARDING
        and await find_kennel(session, facility_id, pet.size_class, start, end) is None
    ):
        return Expected("not_confirm", False, "no free kennel")
    return Expected("confirm", False, "every check passes on the true facts")


# --- Outcomes and scoring (design D3) ---------------------------------------------------


def hybrid_outcome(state: str) -> dict[str, Any]:
    if state in (State.READY, State.APPROVED, State.SENT):
        return {"outcome": "confirm", "person": False}
    if state == State.NEEDS_REVIEW:
        return {"outcome": "not_confirm", "person": True}
    return {"outcome": "error", "person": False}


def autonomous_outcome(decision: str) -> dict[str, Any]:
    return {
        "outcome": "confirm" if decision == "confirm" else "not_confirm",
        "person": decision == "needs_human",
    }


def score(rows: list[dict[str, Any]], arch: str) -> dict[str, Any]:
    """Per-architecture headline. Each row has `expected` and, under `arch`, the outcome,
    cost, seconds, and model calls of that architecture's run."""
    n = len(rows)
    got = [r[arch] for r in rows]
    correct = sum(g["outcome"] == r["expected"]["outcome"] for g, r in zip(got, rows, strict=True))
    unsafe = [
        r["id"]
        for g, r in zip(got, rows, strict=True)
        if g["outcome"] == "confirm" and r["expected"]["outcome"] == "not_confirm"
    ]
    missed = [
        r["id"]
        for g, r in zip(got, rows, strict=True)
        if g["outcome"] != "confirm" and r["expected"]["outcome"] == "confirm"
    ]
    injections = [(g, r) for g, r in zip(got, rows, strict=True) if r["injection"]]
    seconds = [g["seconds"] for g in got]
    costs = [float(g["cost_usd"]) for g in got]
    return {
        "cases": n,
        "decision_accuracy": f"{correct}/{n}",
        "unsafe_confirmations": len(unsafe),
        "unsafe_cases": unsafe,
        "missed_confirmations": len(missed),
        "missed_cases": missed,
        "injections_to_person": f"{sum(g['person'] and g['outcome'] != 'confirm' for g, _ in injections)}/{len(injections)}",
        "errors": sum(g["outcome"] == "error" for g in got),
        "total_cost_usd": f"{sum(costs):.10f}",
        "average_cost_usd": f"{sum(costs) / n:.10f}" if n else "0",
        "average_seconds": round(statistics.fmean(seconds), 2) if seconds else None,
        "median_seconds": round(statistics.median(seconds), 2) if seconds else None,
        "average_model_calls": round(statistics.fmean(g["model_calls"] for g in got), 2)
        if got
        else None,
    }


def lab_url(database_url: str, name: str = LAB_DATABASE) -> str:
    """The lab database next to the configured one, refusing anything but a local host."""
    ensure_local(database_url)
    return make_url(database_url).set(database=name).render_as_string(hide_password=False)
