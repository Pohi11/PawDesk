"""Submit and process booking requests against the dev database, with real model calls.

Run from backend/:
    uv run python -m scripts.bookings submit OWNER_EMAIL "message" [--certificate PATH]
    uv run python -m scripts.bookings process REQUEST_ID [--crash-after STATE]
    uv run python -m scripts.bookings resume REQUEST_ID      # the same as process, after a crash
    uv run python -m scripts.bookings show REQUEST_ID

--crash-after STATE hard-stops the process (os._exit, no cleanup, nothing flushed) right
after the work for STATE commits: `received` stops before extraction, `extracting` stops
after extraction is saved. It exists for the manual kill-and-resume test.
"""

import argparse
import asyncio
import os
import sys
import uuid
from collections import Counter
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db import get_engine, make_sessionmaker
from app.documents import attach_certificate
from app.enums import Step
from app.lifecycle import State
from app.models import BookingRequest, BookingStepResult, Facility, Owner, Span, Trace
from app.orchestrator import process_request
from app.tracing import Tracer


async def submit(
    sessions: async_sessionmaker[AsyncSession],
    owner_email: str,
    message: str,
    certificate: bytes | None = None,
) -> uuid.UUID:
    """Store a new request (and its certificate) for the owner, at the only facility."""
    async with sessions() as session:
        owner = await session.scalar(select(Owner).where(Owner.email == owner_email))
        if owner is None:
            raise SystemExit(f"no owner with email {owner_email!r}")
        facilities = list(await session.scalars(select(Facility.id)))
        if len(facilities) != 1:
            raise SystemExit(f"expected exactly one facility, found {len(facilities)}")
        request = BookingRequest(facility_id=facilities[0], owner_id=owner.id, raw_message=message)
        session.add(request)
        await session.flush()
        if certificate is not None:
            await attach_certificate(session, request.id, certificate)
        await session.commit()
        return request.id


def hard_stop(at: State):
    def hook(finished: State) -> None:
        if finished == at:
            print(f"hard stop after {finished} (os._exit)", flush=True)
            os._exit(137)

    return hook


async def show(sessions: async_sessionmaker[AsyncSession], request_id: uuid.UUID) -> None:
    async with sessions() as session:
        request = await session.get_one(BookingRequest, request_id)
        results = dict(
            (
                await session.execute(
                    select(BookingStepResult.step, BookingStepResult.output).where(
                        BookingStepResult.booking_request_id == request_id
                    )
                )
            ).all()
        )
        traces = list(
            await session.scalars(
                select(Trace).where(Trace.booking_request_id == request_id).order_by(Trace.id)
            )
        )
        print(f"request: {request_id}")
        failed = f" (failed in {request.failed_step})" if request.failed_step else ""
        print(f"state:   {request.status}{failed}")
        if request.last_error:
            print(f"error:   {request.last_error}")
        print(f"steps:   {', '.join(sorted(results)) or '-'}")
        if route := results.get(Step.ROUTE):
            print(f"route:   {route['target']}")
            for reason in route["reasons"]:
                print(f"         - {reason}")
        for n, trace in enumerate(traces, 1):
            spans = list(await session.scalars(select(Span).where(Span.trace_id == trace.id)))
            names = Counter(s.name for s in spans)
            statuses = Counter(str(s.status) for s in spans)
            llm_calls = sum(1 for s in spans if s.kind == "llm")
            cost = await session.scalar(
                select(func.sum(Span.cost_usd)).where(Span.trace_id == trace.id)
            )
            print(
                f"run {n}:   {len(spans)} spans, {llm_calls} model calls, cost {cost or 0} USD, "
                f"statuses {dict(statuses)}, ended {'yes' if trace.ended_at else 'NO'}"
            )
            print(f"         {dict(sorted(names.items()))}")


async def main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(prog="scripts.bookings")
    commands = parser.add_subparsers(dest="command", required=True)
    sub = commands.add_parser("submit")
    sub.add_argument("owner_email")
    sub.add_argument("message")
    sub.add_argument("--certificate", type=Path)
    for name in ("process", "resume"):
        cmd = commands.add_parser(name)
        cmd.add_argument("request_id", type=uuid.UUID)
        cmd.add_argument("--crash-after", type=State, choices=list(State), metavar="STATE")
    commands.add_parser("show").add_argument("request_id", type=uuid.UUID)
    args = parser.parse_args(argv)

    engine = get_engine()
    sessions = make_sessionmaker(engine)
    try:
        if args.command == "submit":
            image = args.certificate.read_bytes() if args.certificate else None
            print(await submit(sessions, args.owner_email, args.message, image))
        elif args.command in ("process", "resume"):
            crash = hard_stop(args.crash_after) if args.crash_after else None
            state = await process_request(
                args.request_id, sessions=sessions, tracer=Tracer(sessions), crash_after=crash
            )
            print(f"ended in: {state}\n")
            await show(sessions, args.request_id)
        else:
            await show(sessions, args.request_id)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
