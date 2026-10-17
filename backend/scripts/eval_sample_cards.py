"""Read the demo samples' cards repeatedly to measure misreads (spec: certificate-evaluation;
change records-year-fidelity, design D2).

Run from backend/:  uv run python -m scripts.eval_sample_cards [--reads N]   (default 20)
Calls the real vision model (costs money). A misread shows up in some reads of an image
and not others, so each card is read N times rather than once. Each run is traced in the
dev database and writes a dated JSON report to evals/results/. Never edit a report by hand.
"""

import argparse
import asyncio
import json
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import func, select

from app.config import get_settings
from app.db import get_engine, make_sessionmaker
from app.demo import DEMO_TODAY, SAMPLE_CARDS, SAMPLES
from app.llm import LLMError
from app.models import Span
from app.prompts.records import PROMPT_VERSION
from app.records import RecordsInvalidOutput, run_records
from app.tracing import Tracer
from scripts.draw_sample_cards import CARDS
from scripts.eval_records import RESULTS_DIR, TIMEZONE, compliance_outcome, match_records

DEFAULT_READS = 20
CONCURRENCY = 4


def printed_records(sample_id: str) -> list[dict[str, Any]]:
    """The records a sample's card was drawn from: what the card prints."""
    _, drawn = CARDS[sample_id]
    return [
        {
            "vaccine": r.vaccine,
            "administered_on": r.administered_on.isoformat(),
            "expires_on": r.expires_on.isoformat(),
        }
        for r in drawn().records
    ]


def sample_stay(sample_id: str) -> dict[str, str]:
    sample = SAMPLES[sample_id]
    return {
        "service": str(sample.service),
        "start": sample.start_date.isoformat(),
        "end": sample.end_date.isoformat(),
    }


# --- Pure scoring ---------------------------------------------------------------------


def score_read(printed: list[dict], read: dict[str, Any], stay: dict[str, str]) -> dict[str, Any]:
    """One read against the card. The card is scored alone: records on file could cover
    for a misread, which would hide it (design D2)."""
    if read["outcome"] == "error":
        return {"failed": True, "misread": False, "flip": False, "silent_flip": False}
    got = [r for r in read["records"] if r["vaccine"]]
    pairs = match_records(printed, got)
    exact = len(pairs) == len(printed) == len(got) and all(
        a["administered_on"] == b["administered_on"] and a["expires_on"] == b["expires_on"]
        for a, b in pairs
    )
    flip = compliance_outcome(got, "dog", stay) != compliance_outcome(printed, "dog", stay)
    return {
        "failed": False,
        "misread": not exact,
        "flip": flip,
        # The dangerous kind: the decision changed AND nothing sent it to a person.
        "silent_flip": flip and read["outcome"] == "clear",
    }


def totals(scores: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "reads": len(scores),
        "failed": sum(s["failed"] for s in scores),
        "misreads": sum(s["misread"] for s in scores),
        "decision_flips": sum(s["flip"] for s in scores),
        "silent_flips": sum(s["silent_flip"] for s in scores),
    }


def build_report(
    cards: dict[str, list[dict[str, Any]]],
    *,
    reads_per_card: int,
    model: str,
    started: datetime,
    trace_id: Any,
    cost: Any,
) -> dict[str, Any]:
    """`cards` maps a sample id to its reads, each {"read": ..., "score": ...}."""
    return {
        "prompt_version": PROMPT_VERSION,
        "model": model,
        "run_at": started.isoformat(),
        "trace_id": str(trace_id),
        "total_cost_usd": str(cost) if cost is not None else None,
        "today": DEMO_TODAY.isoformat(),
        "reads_per_card": reads_per_card,
        "summary": {
            "total": totals([r["score"] for rows in cards.values() for r in rows]),
            "by_card": {sid: totals([r["score"] for r in rows]) for sid, rows in cards.items()},
        },
        "cards": {
            sid: {"printed": printed_records(sid), "stay": sample_stay(sid), "reads": rows}
            for sid, rows in cards.items()
        },
    }


# --- Running --------------------------------------------------------------------------


async def read_card(sample_id: str, today: date) -> dict[str, Any]:
    sample = SAMPLES[sample_id]
    image = (SAMPLE_CARDS / sample.certificate).read_bytes()
    try:
        result = await run_records(image, booked_pet=sample.pet, today=today, timezone=TIMEZONE)
    except (RecordsInvalidOutput, LLMError) as exc:
        return {"records": [], "outcome": "error", "issues": [str(exc)]}
    extraction = result.extraction
    return {
        "records": [r.model_dump(mode="json") for r in extraction.records] if extraction else [],
        "outcome": result.outcome.value,
        "issues": list(result.issues),
    }


async def evaluate(reads: int) -> dict[str, list[dict[str, Any]]]:
    gate = asyncio.Semaphore(CONCURRENCY)

    async def one(sample_id: str) -> dict[str, Any]:
        async with gate:
            read = await read_card(sample_id, DEMO_TODAY)
        return {
            "read": read,
            "score": score_read(printed_records(sample_id), read, sample_stay(sample_id)),
        }

    return {sid: list(await asyncio.gather(*(one(sid) for _ in range(reads)))) for sid in CARDS}


async def main(reads: int) -> None:
    engine = get_engine()
    tracer = Tracer(make_sessionmaker(engine))
    started = datetime.now(UTC)
    try:
        async with tracer.start_trace(f"eval: sample cards {PROMPT_VERSION}") as trace_id:
            cards = await evaluate(reads)
        async with make_sessionmaker(engine)() as s:
            cost = await s.scalar(select(func.sum(Span.cost_usd)).where(Span.trace_id == trace_id))
    finally:
        await engine.dispose()

    report = build_report(
        cards,
        reads_per_card=reads,
        model=get_settings().openrouter_model,
        started=started,
        trace_id=trace_id,
        cost=cost,
    )
    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / f"sample-cards-{PROMPT_VERSION}-{started:%Y%m%dT%H%M%SZ}.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    summary = report["summary"]
    for name, t in [*summary["by_card"].items(), ("TOTAL", summary["total"])]:
        print(
            f"{name:<16} reads {t['reads']:<4} failed {t['failed']:<3} misreads {t['misreads']:<3} "
            f"flips {t['decision_flips']:<3} silent {t['silent_flips']}"
        )
    print(f"\ncost: {report['total_cost_usd']} USD   report: {out.name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Read the sample cards repeatedly.")
    parser.add_argument("--reads", type=int, default=DEFAULT_READS, help="reads per card")
    asyncio.run(main(parser.parse_args().reads))
