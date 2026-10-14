"""The architecture comparison lab: PawDesk's hybrid workflow against a single autonomous
agent, on the same cases, in a separate lab database (spec: architecture-comparison).

Run from backend/ (real model calls, a few tenths of a dollar at most):
    uv run python -m scripts.compare_architectures

Expected outcomes are computed from each case's true facts with the deterministic checks,
not labeled by hand. The hybrid workflow is stopped after drafting, so nothing is sent.
"""

import asyncio
import json
import statistics
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg
from alembic import command
from alembic.config import Config
from sqlalchemy import delete, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession

from app.autonomous import AgentContext, run_autonomous
from app.capacity import find_kennel
from app.compliance import Outcome, VaccineEvidence, check, load_evidence, load_requirements
from app.config import get_settings
from app.db import make_engine, make_sessionmaker
from app.documents import attach_certificate
from app.enums import Service, SpanKind, Step, Vaccine
from app.lifecycle import State
from app.llm import LLMError
from app.models import (
    BookingRequest,
    BookingStepResult,
    Facility,
    Owner,
    Pet,
    Span,
    Trace,
    VaccineRecord,
)
from app.orchestrator import process_request
from app.prompts.autonomous import PROMPT_VERSION as AUTONOMOUS_PROMPT
from app.prompts.reply import PROMPT_VERSION as REPLY_PROMPT
from app.prompts.resolver import PROMPT_VERSION as RESOLVER_PROMPT
from app.structured import InvalidModelOutput
from app.tracing import Tracer
from scripts.seed import ensure_local
from scripts.seed import run as seed_run

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


# --- The lab run (design D4) -------------------------------------------------------------


class LabStop(BaseException):
    """Stops the hybrid workflow right after drafting, before anything can be sent."""


def stop_after_drafting(finished: State) -> None:
    if finished == State.DRAFTING:
        raise LabStop


async def _trace_usage(sessions, trace_ids: list) -> tuple[Decimal, int]:
    async with sessions() as session:
        cost, calls = (
            await session.execute(
                select(
                    func.coalesce(func.sum(Span.cost_usd), 0),
                    func.count().filter(Span.kind == SpanKind.LLM),
                ).where(Span.trace_id.in_(trace_ids))
            )
        ).one()
    return Decimal(cost), calls


async def run_case(
    sessions,
    tracer: Tracer,
    case: dict[str, Any],
    certificate: dict[str, Any] | None,
    *,
    today: date,
    images: Path,
    hybrid_llm: dict[str, Any],
    autonomous_llm: dict[str, Any],
) -> dict[str, Any]:
    image = (images / f"{case['certificate']}.png").read_bytes() if case["certificate"] else None
    async with sessions() as session:
        owner = await session.scalar(select(Owner).where(Owner.email == case["owner"]))
        facility = await session.scalar(select(Facility).order_by(Facility.id).limit(1))
        truth = await expected(session, case, certificate)
        request = BookingRequest(
            facility_id=facility.id, owner_id=owner.id, raw_message=case["message"]
        )
        session.add(request)
        await session.flush()
        if image is not None:
            await attach_certificate(session, request.id, image)
        await session.commit()

    # The hybrid workflow, stopped after drafting: `ready` means it would confirm and send.
    started = time.perf_counter()
    try:
        await process_request(
            request.id,
            sessions=sessions,
            tracer=tracer,
            today=today,
            crash_after=stop_after_drafting,
            **hybrid_llm,
        )
    except LabStop:
        pass
    hybrid_seconds = time.perf_counter() - started
    async with sessions() as session:
        state = (await session.get(BookingRequest, request.id)).status
        reply = await session.scalar(
            select(BookingStepResult.output).where(
                BookingStepResult.booking_request_id == request.id,
                BookingStepResult.step == Step.REPLY,
            )
        )
        hybrid_traces = list(
            await session.scalars(select(Trace.id).where(Trace.booking_request_id == request.id))
        )
    hybrid_cost, hybrid_calls = await _trace_usage(sessions, hybrid_traces)

    # The autonomous agent, in its own trace on the same request.
    ctx = AgentContext(
        facility_id=facility.id,
        facility_name=facility.name,
        owner_id=owner.id,
        today=today,
        message=case["message"],
        image=image,
        mime="image/png" if image is not None else None,
    )
    started = time.perf_counter()
    async with tracer.start_trace(
        "comparison: autonomous", booking_request_id=request.id
    ) as trace_id:
        try:
            agent = await run_autonomous(sessions, ctx, **autonomous_llm)
            agent_json: dict[str, Any] = agent.to_json()
            agent_result = autonomous_outcome(agent.decision)
        except (LLMError, InvalidModelOutput) as exc:
            agent_json = {"error": f"{type(exc).__name__}: {exc}"}
            agent_result = {"outcome": "error", "person": False}
    agent_seconds = time.perf_counter() - started
    agent_cost, agent_calls = await _trace_usage(sessions, [trace_id])

    return {
        "id": case["id"],
        "request_id": str(request.id),
        "injection": case["injection"],
        "expected": {"outcome": truth.outcome, "person": truth.person, "why": truth.why},
        "hybrid": hybrid_outcome(state)
        | {
            "state": str(state),
            "flags": (reply or {}).get("flags", []),
            "cost_usd": str(hybrid_cost),
            "seconds": round(hybrid_seconds, 2),
            "model_calls": hybrid_calls,
        },
        "autonomous": agent_result
        | agent_json
        | {
            "cost_usd": str(agent_cost),
            "seconds": round(agent_seconds, 2),
            "model_calls": agent_calls,
        },
    }


async def run_cases(
    sessions,
    tracer: Tracer,
    cases: list[dict[str, Any]],
    certificates: dict[str, dict[str, Any]],
    **kwargs: Any,
) -> list[dict[str, Any]]:
    rows = []
    for case in cases:  # one at a time: no rate-limit interference between architectures
        certificate = certificates.get(case["certificate"]) if case["certificate"] else None
        rows.append(await run_case(sessions, tracer, case, certificate, **kwargs))
        r = rows[-1]
        print(
            f"{r['id']:<28} expected {r['expected']['outcome']:<12} "
            f"hybrid {r['hybrid']['outcome']:<12} autonomous {r['autonomous']['outcome']}",
            flush=True,
        )
    return rows


def build_report(
    rows: list[dict[str, Any]], *, cases_doc: dict[str, Any], model: str, run_at: str
) -> dict[str, Any]:
    hybrid, autonomous = score(rows, "hybrid"), score(rows, "autonomous")
    total = Decimal(hybrid["total_cost_usd"]) + Decimal(autonomous["total_cost_usd"])
    return {
        "kind": "comparison",
        "cases_version": cases_doc["version"],
        "today": cases_doc["today"],
        "model": model,
        "prompt_version": f"hybrid ({REPLY_PROMPT}, {RESOLVER_PROMPT}) vs {AUTONOMOUS_PROMPT}",
        "run_at": run_at,
        "total_cost_usd": str(total),
        "headline": {"hybrid": hybrid, "autonomous": autonomous},
        "cases": rows,
    }


def certificate_pets(cases: list[dict[str, Any]]) -> set[tuple[str, str]]:
    """(owner email, pet name) for every case that brings a certificate."""
    return {(c["owner"], c["pet"]) for c in cases if c["certificate"] and c["pet"]}


async def clear_records_on_file(session: AsyncSession, pets: set[tuple[str, str]]) -> int:
    """Remove those pets' vaccine records, so their certificate alone decides compliance.

    The seed gives every pet valid records relative to its "today"; left in place, they
    would cover most stays whatever the certificate said, and certificate reading (where
    the two architectures differ most) would rarely matter.
    """
    removed = 0
    for email, name in sorted(pets):
        pet_id = await session.scalar(
            select(Pet.id)
            .join(Owner, Owner.id == Pet.owner_id)
            .where(Owner.email == email, Pet.name == name)
        )
        result = await session.execute(delete(VaccineRecord).where(VaccineRecord.pet_id == pet_id))
        removed += result.rowcount
    return removed


async def _clear(url: str, pets: set[tuple[str, str]]) -> None:
    engine = make_engine(url)
    try:
        async with make_sessionmaker(engine)() as session, session.begin():
            await clear_records_on_file(session, pets)
    finally:
        await engine.dispose()


def prepare_lab(url: str, today: date, cases: list[dict[str, Any]]) -> None:
    """Create the lab database if needed, migrate it from scratch, seed it, and clear the
    records on file of pets that bring a certificate."""
    admin = make_url(url).set(database="postgres", drivername="postgresql")
    name = make_url(url).database
    with psycopg.connect(admin.render_as_string(hide_password=False), autocommit=True) as conn:
        exists = conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,)).fetchone()
        if not exists:
            conn.execute(f'CREATE DATABASE "{name}"')
    backend = Path(__file__).resolve().parents[1]
    cfg = Config(str(backend / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    asyncio.run(seed_run(url, today))
    asyncio.run(_clear(url, certificate_pets(cases)))


async def main_async(url: str) -> Path:
    cases_doc = json.loads(CASES.read_text(encoding="utf-8"))
    truth = json.loads(TRUTH.read_text(encoding="utf-8"))
    certificates = {c["id"]: c for c in truth["certificates"]}
    today = date.fromisoformat(cases_doc["today"])
    engine = make_engine(url)
    sessions = make_sessionmaker(engine)
    run_at = datetime.now(UTC)
    try:
        rows = await run_cases(
            sessions,
            Tracer(sessions),
            cases_doc["cases"],
            certificates,
            today=today,
            images=TRUTH.parent / "images",
            hybrid_llm={},
            autonomous_llm={},
        )
    finally:
        await engine.dispose()
    report = build_report(
        rows, cases_doc=cases_doc, model=get_settings().openrouter_model, run_at=run_at.isoformat()
    )
    out = EVALS / "results" / f"comparison-{run_at:%Y%m%dT%H%M%SZ}.json"
    text = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    out.write_text(text, encoding="utf-8", newline="\n")
    for arch in ("hybrid", "autonomous"):
        h = report["headline"][arch]
        print(
            f"{arch:<11} accuracy {h['decision_accuracy']:<6} unsafe {h['unsafe_confirmations']} "
            f"missed {h['missed_confirmations']} injections-to-person {h['injections_to_person']} "
            f"errors {h['errors']} cost {h['total_cost_usd']} avg {h['average_seconds']} s "
            f"calls {h['average_model_calls']}"
        )
    return out


def main() -> None:
    url = lab_url(get_settings().database_url)
    cases_doc = json.loads(CASES.read_text(encoding="utf-8"))
    prepare_lab(url, date.fromisoformat(cases_doc["today"]), cases_doc["cases"])
    print(f"report: {asyncio.run(main_async(url))}")


if __name__ == "__main__":
    main()
