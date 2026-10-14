"""Read-only views of everything PawDesk records about its runs (spec: observability-api).

Requests, their steps and transitions, every span of every run, metrics computed in SQL,
and the saved eval reports. Nothing here writes.
"""

import json
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import SpanKind, SpanStatus, Step
from app.lifecycle import State
from app.models import (
    Approval,
    BookingRequest,
    BookingStepResult,
    BookingTransition,
    OutboundMessage,
    Owner,
    Pet,
    Span,
    Trace,
)

RESULTS_DIR = Path(__file__).resolve().parents[1] / "evals" / "results"
RESTING = frozenset({State.SENT, State.NEEDS_REVIEW, State.FAILED})


def _iso(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


def _money(value: Decimal | None) -> str:
    return str(value if value is not None else Decimal(0))


# --- Requests ---------------------------------------------------------------------------


async def list_requests(session: AsyncSession, limit: int = 50) -> list[dict[str, Any]]:
    cost = (
        select(func.sum(Span.cost_usd))
        .join(Trace, Trace.id == Span.trace_id)
        .where(Trace.booking_request_id == BookingRequest.id)
        .scalar_subquery()
    )
    reply = (
        select(BookingStepResult.output)
        .where(
            BookingStepResult.booking_request_id == BookingRequest.id,
            BookingStepResult.step == Step.REPLY,
        )
        .scalar_subquery()
    )
    intake = (
        select(BookingStepResult.output)
        .where(
            BookingStepResult.booking_request_id == BookingRequest.id,
            BookingStepResult.step == Step.INTAKE,
        )
        .scalar_subquery()
    )
    rows = await session.execute(
        select(BookingRequest, Owner.full_name, Pet.name, cost, reply, intake)
        .join(Owner, Owner.id == BookingRequest.owner_id)
        .outerjoin(Pet, Pet.id == BookingRequest.pet_id)
        .order_by(BookingRequest.created_at.desc(), BookingRequest.id.desc())
        .limit(limit)
    )
    result = []
    for request, owner, pet, total, reply_out, intake_out in rows:
        intent = (intake_out or {}).get("intent") or {}
        result.append(
            {
                "id": str(request.id),
                "status": str(request.status),
                "created_at": _iso(request.created_at),
                "owner": owner,
                "pet": pet,
                "service": intent.get("service"),
                "start_date": intent.get("start_date"),
                "end_date": intent.get("end_date"),
                "cost_usd": _money(total),
                "flagged": (reply_out or {}).get("target") == State.NEEDS_REVIEW,
            }
        )
    return result


def span_json(span: Span) -> dict[str, Any]:
    return {
        "id": str(span.id),
        "trace_id": str(span.trace_id),
        "parent_span_id": str(span.parent_span_id) if span.parent_span_id else None,
        "name": span.name,
        "kind": str(span.kind),
        "status": str(span.status),
        "started_at": _iso(span.started_at),
        "ended_at": _iso(span.ended_at),
        "model": span.model,
        "prompt_tokens": span.prompt_tokens,
        "completion_tokens": span.completion_tokens,
        "cost_usd": str(span.cost_usd) if span.cost_usd is not None else None,
        "input": span.input,
        "output": span.output,
        "attributes": span.attributes,
        "error": span.error,
    }


async def request_detail(session: AsyncSession, request_id: uuid.UUID) -> dict[str, Any]:
    request = await session.get(BookingRequest, request_id)
    if request is None:
        raise LookupError(f"no booking request {request_id}")
    owner = await session.get_one(Owner, request.owner_id)
    pet = await session.get(Pet, request.pet_id) if request.pet_id else None

    transitions = await session.scalars(
        select(BookingTransition)
        .where(BookingTransition.booking_request_id == request_id)
        .order_by(BookingTransition.created_at, BookingTransition.id)
    )
    steps = await session.execute(
        select(BookingStepResult.step, BookingStepResult.output, BookingStepResult.created_at)
        .where(BookingStepResult.booking_request_id == request_id)
        .order_by(BookingStepResult.created_at, BookingStepResult.id)
    )
    approvals = await session.scalars(
        select(Approval).where(Approval.booking_request_id == request_id).order_by(Approval.id)
    )
    message = await session.scalar(
        select(OutboundMessage).where(OutboundMessage.booking_request_id == request_id)
    )
    traces = list(
        await session.scalars(
            select(Trace).where(Trace.booking_request_id == request_id).order_by(Trace.id)
        )
    )
    spans = list(
        await session.scalars(
            select(Span)
            .where(Span.trace_id.in_([t.id for t in traces]))
            .order_by(Span.started_at, Span.id)
        )
    )
    return {
        "id": str(request.id),
        "status": str(request.status),
        "failed_step": str(request.failed_step) if request.failed_step else None,
        "last_error": request.last_error,
        "created_at": _iso(request.created_at),
        "owner": owner.full_name,
        "pet": pet.name if pet else None,
        "raw_message": request.raw_message,
        "transitions": [
            {
                "from": str(t.from_status),
                "to": str(t.to_status),
                "actor": str(t.actor),
                "reason": t.reason,
                "at": _iso(t.created_at),
            }
            for t in transitions
        ],
        "steps": {str(step): output for step, output, _ in steps},
        "approvals": [
            {
                "action": str(a.action),
                "staff_name": a.staff_name,
                "reason": a.reason,
                "edited_reply": a.edited_reply,
                "at": _iso(a.created_at),
            }
            for a in approvals
        ],
        "message": (
            {"kind": message.kind, "subject": message.subject, "body": message.body}
            if message
            else None
        ),
        "traces": [
            {
                "id": str(t.id),
                "name": t.name,
                "started_at": _iso(t.started_at),
                "ended_at": _iso(t.ended_at),
                "spans": [span_json(s) for s in spans if s.trace_id == t.id],
            }
            for t in traces
        ],
    }


async def snapshot(session: AsyncSession, request_id: uuid.UUID) -> dict[str, Any]:
    """The light view the live stream sends: state, whether the reply was flagged (None
    until drafted), and span timing, with no payloads."""
    row = (
        await session.execute(
            select(BookingRequest.status, BookingRequest.failed_step).where(
                BookingRequest.id == request_id
            )
        )
    ).one_or_none()
    if row is None:
        raise LookupError(f"no booking request {request_id}")
    status, failed_step = row
    reply = await session.scalar(
        select(BookingStepResult.output).where(
            BookingStepResult.booking_request_id == request_id,
            BookingStepResult.step == Step.REPLY,
        )
    )
    rows = await session.execute(
        select(Span)
        .join(Trace, Trace.id == Span.trace_id)
        .where(Trace.booking_request_id == request_id)
        .order_by(Span.started_at, Span.id)
    )
    spans = [
        {
            k: v
            for k, v in span_json(s).items()
            if k not in ("input", "output", "attributes", "error")
        }
        for s in rows.scalars()
    ]
    return {
        "status": str(status),
        "failed_step": str(failed_step) if failed_step else None,
        "flagged": reply["target"] == State.NEEDS_REVIEW if reply else None,
        "spans": spans,
    }


def is_resting(snap: dict[str, Any]) -> bool:
    return snap["status"] in RESTING and all(
        s["status"] != SpanStatus.RUNNING for s in snap["spans"]
    )


# --- Metrics ----------------------------------------------------------------------------


async def metrics(session: AsyncSession) -> dict[str, Any]:
    by_state = dict(
        (
            await session.execute(
                select(BookingRequest.status, func.count()).group_by(BookingRequest.status)
            )
        ).all()
    )

    per_request = (
        select(Trace.booking_request_id, func.sum(Span.cost_usd).label("cost"))
        .join(Span, Span.trace_id == Trace.id)
        .where(Trace.booking_request_id.is_not(None))
        .group_by(Trace.booking_request_id)
        .subquery()
    )
    total, average, costed = (
        await session.execute(
            select(
                func.sum(per_request.c.cost),
                func.avg(per_request.c.cost),
                func.count(),
            )
        )
    ).one()

    steps = await session.execute(
        select(
            Span.name,
            func.count(),
            func.sum(Span.cost_usd),
            func.avg(func.extract("epoch", Span.ended_at - Span.started_at)),
        )
        .join(Trace, Trace.id == Span.trace_id)
        .where(Span.kind == SpanKind.LLM, Trace.booking_request_id.is_not(None))
        .group_by(Span.name)
        .order_by(Span.name)
    )

    duration = func.extract("epoch", Trace.ended_at - Trace.started_at)
    p50, p95, runs = (
        await session.execute(
            select(
                func.percentile_cont(0.5).within_group(duration),
                func.percentile_cont(0.95).within_group(duration),
                func.count(),
            ).where(Trace.booking_request_id.is_not(None), Trace.ended_at.is_not(None))
        )
    ).one()

    flagged, drafted = (
        await session.execute(
            select(
                func.count().filter(
                    BookingStepResult.output["target"].astext == State.NEEDS_REVIEW
                ),
                func.count(),
            ).where(BookingStepResult.step == Step.REPLY)
        )
    ).one()

    return {
        "requests_by_state": {str(state): n for state, n in by_state.items()},
        "cost": {
            "total_usd": _money(total),
            "average_per_request_usd": _money(round(average, 10) if average else None),
            "requests_with_cost": costed,
        },
        "model_steps": [
            {
                "name": name,
                "calls": calls,
                "cost_usd": _money(cost),
                "average_seconds": round(float(avg), 3) if avg is not None else None,
            }
            for name, calls, cost, avg in steps
        ],
        "run_seconds": {
            "p50": round(float(p50), 3) if p50 is not None else None,
            "p95": round(float(p95), 3) if p95 is not None else None,
            "runs": runs,
        },
        "flag_rate": {
            "flagged": flagged,
            "drafted": drafted,
            "rate": round(flagged / drafted, 4) if drafted else None,
        },
    }


# --- Eval reports -----------------------------------------------------------------------

HEADLINES = {
    "records": (
        "decision_agreement",
        "silent_disagreements",
        "vaccine_recall",
        "expiry_accuracy",
        "invented_expiries",
        "sent_to_review",
        "errors",
    ),
}


def eval_reports(results_dir: Path = RESULTS_DIR) -> list[dict[str, Any]]:
    reports = []
    for path in sorted(results_dir.glob("*.json")):
        report = json.loads(path.read_text(encoding="utf-8"))
        kind = path.stem.split("-", 1)[0]
        summary = report.get("summary", {})
        if kind == "intake":
            headline = {
                "cases_fully_matched": f"{summary['cases_fully_matched']}/{summary['cases']}",
                "injections_sent_to_review": (
                    f"{summary['injections_sent_to_review']}/{summary['injection_cases']}"
                ),
            }
        elif kind in HEADLINES:
            total = summary.get("total", {})
            headline = {key: total.get(key) for key in HEADLINES[kind]}
        else:
            headline = report.get("headline", {})
        benchmark = report.get("benchmark")
        reports.append(
            {
                "file": path.name,
                "kind": kind,
                # Reports from before benchmarks were versioned are v1 (as the eval runner reads them).
                "benchmark": benchmark.get("version", "v1")
                if isinstance(benchmark, dict)
                else None,
                "prompt_version": report.get("prompt_version"),
                "model": report.get("model"),
                "run_at": report.get("run_at"),
                "cost_usd": str(report.get("total_cost_usd")),
                "headline": headline,
            }
        )
    reports.sort(key=lambda r: r["run_at"] or "")
    return reports
