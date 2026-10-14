"""Evaluate intake against the labeled message set (spec: booking-intake).

Run from backend/:  uv run python -m scripts.eval_intake
Calls the real model (costs money). Each run is traced in the dev database and writes a
dated JSON report to evals/results/. Never edit a report by hand: it is a measurement.
"""

import asyncio
import json
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func, select

from app.config import get_settings
from app.db import get_engine, make_sessionmaker
from app.intake import IntakeInvalidOutput, PetRef, run_intake
from app.models import Span
from app.prompts.intake import PROMPT_VERSION
from app.tracing import Tracer

EVALS_DIR = Path(__file__).resolve().parents[1] / "evals"
CASES_FILE = EVALS_DIR / "intake_cases.json"
FIELDS = ("pet", "service", "start_date", "end_date", "outcome")
SKIP = "*"


def load_cases(path: Path = CASES_FILE) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def score_case(expected: dict[str, Any], actual: dict[str, Any]) -> dict[str, bool | None]:
    """Per field: True (matched), False (wrong), None (not scored: expected is '*')."""
    return {f: None if expected[f] == SKIP else expected[f] == actual.get(f) for f in FIELDS}


def summarize(scored: list[dict[str, Any]]) -> dict[str, Any]:
    per_field = {}
    for f in FIELDS:
        marks = [c["fields"][f] for c in scored if c["fields"][f] is not None]
        per_field[f] = {"matched": sum(marks), "scored": len(marks)}
    exact = sum(all(v is not False for v in c["fields"].values()) for c in scored)
    injections = [c for c in scored if c["injection"]]
    return {
        "cases": len(scored),
        "cases_fully_matched": exact,
        "per_field": per_field,
        "injection_cases": len(injections),
        "injections_sent_to_review": sum(
            c["actual"]["outcome"] == "needs_review" for c in injections
        ),
    }


async def run_case(case: dict[str, Any], today: date, timezone: str, **llm_kwargs: Any) -> dict:
    pets = [PetRef(id=uuid.uuid4(), name=name) for name in case["pets"]]
    names = {p.id: p.name for p in pets}
    try:
        result = await run_intake(
            case["message"], pets=pets, today=today, timezone=timezone, **llm_kwargs
        )
    except IntakeInvalidOutput as exc:
        return {f: None for f in FIELDS} | {"outcome": "error", "issues": [str(exc)]}
    intent = result.intent
    return {
        "pet": names.get(result.pet_id),
        "service": intent.service.value if intent and intent.service else None,
        "start_date": intent.start_date.isoformat() if intent and intent.start_date else None,
        "end_date": intent.end_date.isoformat() if intent and intent.end_date else None,
        "outcome": result.outcome.value,
        "issues": list(result.issues),
    }


async def evaluate(
    cases_doc: dict[str, Any],
    run: Callable[..., Awaitable[dict[str, Any]]] = run_case,
    **llm_kwargs: Any,
) -> list[dict[str, Any]]:
    today = date.fromisoformat(cases_doc["today"])
    scored = []
    for case in cases_doc["cases"]:
        actual = await run(case, today, cases_doc["timezone"], **llm_kwargs)
        scored.append(
            {
                "id": case["id"],
                "injection": case["injection"],
                "expected": case["expected"],
                "actual": actual,
                "fields": score_case(case["expected"], actual),
            }
        )
    return scored


async def main() -> None:
    engine = get_engine()
    tracer = Tracer(make_sessionmaker(engine))
    started = datetime.now(UTC)
    try:
        async with tracer.start_trace(f"eval: intake {PROMPT_VERSION}") as trace_id:
            scored = await evaluate(load_cases())
        async with make_sessionmaker(engine)() as s:
            cost = await s.scalar(select(func.sum(Span.cost_usd)).where(Span.trace_id == trace_id))
    finally:
        await engine.dispose()

    summary = summarize(scored)
    report = {
        "prompt_version": PROMPT_VERSION,
        "model": get_settings().openrouter_model,
        "run_at": started.isoformat(),
        "trace_id": str(trace_id),
        "total_cost_usd": str(cost) if cost is not None else None,
        "summary": summary,
        "cases": scored,
    }
    out = EVALS_DIR / "results" / f"intake-{started:%Y%m%dT%H%M%SZ}.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    for c in scored:
        misses = [f for f, ok in c["fields"].items() if ok is False]
        print(f"{'PASS' if not misses else 'MISS'}  {c['id']:<34} {', '.join(misses)}")
    print(f"\n{summary['cases_fully_matched']}/{summary['cases']} cases fully matched")
    for f, v in summary["per_field"].items():
        print(f"  {f:<11} {v['matched']}/{v['scored']}")
    print(
        f"  injections sent to review: "
        f"{summary['injections_sent_to_review']}/{summary['injection_cases']}"
    )
    print(f"cost: {report['total_cost_usd']} USD   report: {out.relative_to(EVALS_DIR.parent)}")


if __name__ == "__main__":
    asyncio.run(main())
