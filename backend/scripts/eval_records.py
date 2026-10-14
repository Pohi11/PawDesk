"""Evaluate the records step on the synthetic certificate benchmark (spec: certificate-evaluation).

Run from backend/:  uv run python -m scripts.eval_records
Calls the real vision model (costs money). Each run is traced in the dev database and writes
a dated JSON report to evals/results/. Never edit a report by hand: it is a measurement.
"""

import asyncio
import itertools
import json
from collections import defaultdict
from collections.abc import Awaitable, Callable
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import func, select

from app.compliance import VaccineEvidence, check
from app.config import get_settings
from app.db import get_engine, make_sessionmaker
from app.enums import Service, Species, Vaccine
from app.llm import LLMError
from app.models import Span
from app.prompts.records import PROMPT_VERSION
from app.records import RecordsInvalidOutput, run_records
from app.tracing import Tracer
from scripts.generate_certificates import CERT_DIR, TRUTH_FILE
from scripts.seed import RULES

RESULTS_DIR = CERT_DIR.parent / "results"
TIMEZONE = "America/Chicago"


def load_truth() -> dict[str, Any]:
    return json.loads(TRUTH_FILE.read_text(encoding="utf-8"))


# --- Pure scoring ---------------------------------------------------------------------


def _date_hits(truth: dict, got: dict) -> int:
    return (truth["administered_on"] == got["administered_on"]) + (
        truth["expires_on"] == got["expires_on"]
    )


def match_records(truth: list[dict], got: list[dict]) -> list[tuple[dict, dict]]:
    """Pair records with the same vaccine. With duplicates, keep the pairing that matches
    the most dates, so a correct record isn't scored against the wrong twin."""
    pairs = []
    for vaccine in {r["vaccine"] for r in truth}:
        t = [r for r in truth if r["vaccine"] == vaccine]
        g = [r for r in got if r["vaccine"] == vaccine]
        if not g:
            continue
        k = min(len(t), len(g))
        best = max(
            (
                list(zip(tc, gc, strict=True))
                for tc in itertools.permutations(t, k)
                for gc in itertools.combinations(g, k)
            ),
            key=lambda ps: sum(_date_hits(a, b) for a, b in ps),
        )
        pairs += best
    return pairs


def compliance_outcome(records: list[dict], species: str, stay: dict[str, str]) -> str:
    required = RULES[(Service(stay["service"]), Species(species))]
    evidence = [
        VaccineEvidence(
            Vaccine(r["vaccine"]),
            date.fromisoformat(r["administered_on"]),
            date.fromisoformat(r["expires_on"]) if r["expires_on"] else None,
        )
        for r in records
        if r["vaccine"]
    ]
    result = check(
        required, evidence, date.fromisoformat(stay["start"]), date.fromisoformat(stay["end"])
    )
    return result.outcome.value


def score_certificate(cert: dict, actual: dict, stay: dict[str, str]) -> dict[str, Any]:
    truth, got = cert["records"], actual["records"]
    pairs = match_records(truth, got)
    mapped = [r for r in got if r["vaccine"]]
    truth_decision = compliance_outcome(truth, cert["species"], stay)
    got_decision = (
        compliance_outcome(got, cert["species"], stay) if actual["outcome"] != "error" else "error"
    )
    agrees = truth_decision == got_decision
    return {
        "truth_records": len(truth),
        "extracted_records": len(mapped),
        "matched": len(pairs),
        "given_correct": sum(a["administered_on"] == b["administered_on"] for a, b in pairs),
        "expiry_correct": sum(a["expires_on"] == b["expires_on"] for a, b in pairs),
        "invented_expiries": sum(
            a["expires_on"] is None and b["expires_on"] is not None for a, b in pairs
        ),
        "pet_name_correct": (actual["pet_name"] or "").strip().casefold()
        == cert["pet_name"].casefold(),
        "truth_decision": truth_decision,
        "extracted_decision": got_decision,
        "decision_agrees": agrees,
        # The dangerous kind: the decision is wrong AND nothing sent it to a person.
        "silent_disagreement": not agrees and actual["outcome"] == "clear",
    }


def summarize(scored: list[dict[str, Any]]) -> dict[str, Any]:
    def totals(rows: list[dict]) -> dict[str, Any]:
        s = {
            k: sum(r["score"][k] for r in rows)
            for k in (
                "truth_records",
                "extracted_records",
                "matched",
                "given_correct",
                "expiry_correct",
                "invented_expiries",
            )
        }
        return {
            "certificates": len(rows),
            "vaccine_recall": f"{s['matched']}/{s['truth_records']}",
            "vaccine_precision": f"{s['matched']}/{s['extracted_records']}",
            "given_accuracy": f"{s['given_correct']}/{s['matched']}",
            "expiry_accuracy": f"{s['expiry_correct']}/{s['matched']}",
            "invented_expiries": s["invented_expiries"],
            "pet_name_accuracy": f"{sum(r['score']['pet_name_correct'] for r in rows)}/{len(rows)}",
            "decision_agreement": f"{sum(r['score']['decision_agrees'] for r in rows)}/{len(rows)}",
            "silent_disagreements": sum(r["score"]["silent_disagreement"] for r in rows),
            "sent_to_review": sum(r["actual"]["outcome"] == "needs_review" for r in rows),
            "errors": sum(r["actual"]["outcome"] == "error" for r in rows),
        }

    by_variant: dict[str, list] = defaultdict(list)
    for row in scored:
        by_variant[row["variant"]].append(row)
    return {
        "total": totals(scored),
        "by_variant": {v: totals(r) for v, r in sorted(by_variant.items())},
    }


# --- Running --------------------------------------------------------------------------


async def run_certificate(cert: dict, today: date, **llm_kwargs: Any) -> dict[str, Any]:
    image = (CERT_DIR / cert["file"]).read_bytes()
    try:
        result = await run_records(
            image, booked_pet=cert["pet_name"], today=today, timezone=TIMEZONE, **llm_kwargs
        )
    except (RecordsInvalidOutput, LLMError) as exc:
        # A failed call is a real outcome (the request would go to `failed` for staff),
        # so it is scored, not allowed to crash the run.
        return {"pet_name": None, "records": [], "outcome": "error", "issues": [str(exc)]}
    extraction = result.extraction
    return {
        "pet_name": extraction.pet_name if extraction else None,
        "records": [r.model_dump(mode="json") for r in extraction.records] if extraction else [],
        "outcome": result.outcome.value,
        "issues": list(result.issues),
    }


async def evaluate(
    truth_doc: dict[str, Any],
    run: Callable[..., Awaitable[dict[str, Any]]] = run_certificate,
    **llm_kwargs: Any,
) -> list[dict[str, Any]]:
    today = date.fromisoformat(truth_doc["today"])
    scored = []
    for cert in truth_doc["certificates"]:
        actual = await run(cert, today, **llm_kwargs)
        scored.append(
            {
                "id": cert["id"],
                "layout": cert["layout"],
                "variant": cert["variant"],
                "actual": actual,
                "score": score_certificate(cert, actual, truth_doc["reference_stay"]),
            }
        )
    return scored


async def main() -> None:
    engine = get_engine()
    tracer = Tracer(make_sessionmaker(engine))
    started = datetime.now(UTC)
    truth_doc = load_truth()
    try:
        async with tracer.start_trace(f"eval: records {PROMPT_VERSION}") as trace_id:
            scored = await evaluate(truth_doc)
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
        "benchmark": {
            "seed": truth_doc["seed"],
            "certificates": len(truth_doc["certificates"]),
            "reference_stay": truth_doc["reference_stay"],
        },
        "summary": summary,
        "certificates": scored,
    }
    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / f"records-{started:%Y%m%dT%H%M%SZ}.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    for row in scored:
        sc = row["score"]
        flag = (
            "ok " if sc["decision_agrees"] else ("SILENT" if sc["silent_disagreement"] else "diff")
        )
        print(
            f"{flag:<6} {row['id']}  {row['layout']:<5} {row['variant']:<15} "
            f"matched {sc['matched']}/{sc['truth_records']}  expiry {sc['expiry_correct']}/{sc['matched']}"
            f"  {row['actual']['outcome']}"
        )
    print()
    for name, t in [("TOTAL", summary["total"]), *summary["by_variant"].items()]:
        print(
            f"{name:<15} recall {t['vaccine_recall']:<7} precision {t['vaccine_precision']:<7} "
            f"given {t['given_accuracy']:<7} expiry {t['expiry_accuracy']:<7} "
            f"invented {t['invented_expiries']}  decisions {t['decision_agreement']:<6} "
            f"silent {t['silent_disagreements']}  review {t['sent_to_review']}"
        )
    print(
        f"\ncost: {report['total_cost_usd']} USD   report: {out.relative_to(CERT_DIR.parent.parent)}"
    )


if __name__ == "__main__":
    asyncio.run(main())
