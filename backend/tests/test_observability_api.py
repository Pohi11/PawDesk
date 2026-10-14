"""Spec: observability-api, through the FastAPI app against a real database."""

import json
from decimal import Decimal

import httpx
import pytest

from app.api import get_results_dir
from app.db import get_sessionmaker
from app.documents import attach_certificate
from app.llm import RetryPolicy, make_client
from app.main import app
from app.models import BookingRequest
from app.orchestrator import process_request
from tests.test_llm import fake_settings
from tests.test_orchestrator import (
    CERTIFICATE,
    CLEAR_STATES,
    INTENT,
    ONE_DAY_REPLY,
    PNG,
    START,
    TODAY,
    FakeModel,
)

spec = pytest.mark.spec
INTAKE_CALL_COST = Decimal("0.0000942")  # what the scripted model reports per call


@pytest.fixture
async def api(committed):
    app.dependency_overrides[get_sessionmaker] = lambda: committed
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def run(committed, desk, tracer):
    """Submit and fully process a request against a scripted model."""

    async def make(model=None, message="Can Biscuit board March 10 to 14?"):
        async with committed() as s:
            request = BookingRequest(
                facility_id=desk.facility_id, owner_id=desk.owner_id, raw_message=message
            )
            s.add(request)
            await s.flush()
            await attach_certificate(s, request.id, PNG)
            await s.commit()
        settings = fake_settings()
        await process_request(
            request.id,
            sessions=committed,
            tracer=tracer,
            today=TODAY,
            client=make_client(settings, transport=httpx.MockTransport(model or FakeModel())),
            settings=settings,
            policy=RetryPolicy(max_attempts=1),
        )
        return str(request.id)

    return make


def another_pet():
    return FakeModel(records=CERTIFICATE | {"pet_name": "Max"})


# --- Requests can be listed and inspected -----------------------------------------------


@spec("observability-api", "Requests can be listed and inspected")
async def test_list_shows_cost_and_flag(api, run):
    sent = await run()
    waiting = await run(another_pet())

    rows = {r["id"]: r for r in (await api.get("/requests")).json()}

    assert (rows[sent]["status"], rows[sent]["flagged"]) == ("sent", False)
    assert (rows[waiting]["status"], rows[waiting]["flagged"]) == ("needs_review", True)
    assert all(Decimal(r["cost_usd"]) > 0 for r in rows.values())
    assert rows[sent]["pet"] == "Biscuit" and rows[sent]["service"] == "boarding"
    assert next(iter(rows)) == waiting  # newest first


@spec("observability-api", "Requests can be listed and inspected")
async def test_detail_shows_the_whole_run(api, run):
    request_id = await run()

    detail = (await api.get(f"/requests/{request_id}")).json()

    assert [t["to"] for t in detail["transitions"]] == [str(s) for s in CLEAR_STATES]
    assert set(detail["steps"]) == {"intake", "records", "checks", "route", "reply"}
    assert detail["message"]["kind"] == "reply"
    [trace] = detail["traces"]
    spans = {s["name"]: s for s in trace["spans"]}
    assert spans["intake"]["parent_span_id"] == spans["extract"]["id"]
    assert spans["intake.extract"]["kind"] == "llm"
    assert spans["intake.extract"]["prompt_tokens"] == 42
    assert all(s["started_at"] and s["ended_at"] for s in trace["spans"])


@spec("observability-api", "Requests can be listed and inspected")
async def test_unknown_request_is_404(api):
    response = await api.get("/requests/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404


# --- Metrics summarize cost, latency, and flags -----------------------------------------


@spec("observability-api", "Metrics summarize cost, latency, and flags")
async def test_cost_per_step(api, run):
    await run(FakeModel(records=CERTIFICATE | {"pet_name": "Max"}))
    await run(another_pet())

    metrics = (await api.get("/metrics")).json()

    steps = {s["name"]: s for s in metrics["model_steps"]}
    assert steps["intake.extract"]["calls"] == 2
    assert Decimal(steps["intake.extract"]["cost_usd"]) == 2 * INTAKE_CALL_COST
    assert metrics["run_seconds"]["runs"] == 2
    assert metrics["run_seconds"]["p50"] is not None
    assert metrics["requests_by_state"] == {"needs_review": 2}


@spec("observability-api", "Metrics summarize cost, latency, and flags")
async def test_flag_rate(api, run):
    await run()
    await run(another_pet())
    grooming = INTENT | {"service": "grooming", "end_date": START.isoformat()}
    await run(FakeModel(intake=grooming, reply=ONE_DAY_REPLY))

    flag = (await api.get("/metrics")).json()["flag_rate"]

    assert (flag["flagged"], flag["drafted"]) == (1, 3)
    assert flag["rate"] == round(1 / 3, 4)


# --- Eval reports are listed over time --------------------------------------------------


@spec("observability-api", "Eval reports are listed over time")
async def test_reports_listed_in_date_order(api, tmp_path):
    (tmp_path / "records-v2-x.json").write_text(
        json.dumps(
            {
                "prompt_version": "records-v1",
                "model": "m",
                "run_at": "2026-10-14T15:54:39+00:00",
                "total_cost_usd": "0.0237",
                "benchmark": {"version": "v2"},
                "summary": {"total": {"decision_agreement": "33/36", "silent_disagreements": 2}},
            }
        )
    )
    (tmp_path / "intake-y.json").write_text(
        json.dumps(
            {
                "prompt_version": "intake-v1",
                "model": "m",
                "run_at": "2026-10-14T15:05:30+00:00",
                "total_cost_usd": "0.0107",
                "summary": {
                    "cases": 16,
                    "cases_fully_matched": 16,
                    "injection_cases": 3,
                    "injections_sent_to_review": 3,
                },
            }
        )
    )
    app.dependency_overrides[get_results_dir] = lambda: tmp_path

    reports = (await api.get("/evals")).json()

    assert [(r["kind"], r["benchmark"]) for r in reports] == [("intake", None), ("records", "v2")]
    assert reports[0]["headline"] == {
        "cases_fully_matched": "16/16",
        "injections_sent_to_review": "3/3",
    }
    assert reports[1]["headline"]["silent_disagreements"] == 2


async def test_real_results_folder_is_readable(api):
    reports = (await api.get("/evals")).json()

    assert {r["kind"] for r in reports} >= {"intake", "records"}
