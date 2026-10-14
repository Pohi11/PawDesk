"""Spec: observability-api, through the FastAPI app against a real database."""

import asyncio
import json
import uuid
from decimal import Decimal

import httpx
import pytest
from sqlalchemy import func, select

from app.api import StreamTiming, get_llm_kwargs, get_results_dir, get_stream_timing
from app.db import get_sessionmaker
from app.demo import SAMPLES
from app.documents import attach_certificate
from app.llm import RetryPolicy, make_client
from app.main import app
from app.models import BookingRequest, Owner, Pet
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


@spec("observability-api", "Requests identify the matched pet")
async def test_matched_pet_is_identified(api, run, committed, desk):
    async with committed() as s:
        (await s.get(Pet, desk.biscuit_id)).breed = "Beagle"
        await s.commit()
    request_id = await run()

    [row] = (await api.get("/requests")).json()
    detail = (await api.get(f"/requests/{request_id}")).json()

    for found in (row, detail):
        assert found["pet"] == "Biscuit"
        assert found["pet_id"] == str(desk.biscuit_id)
        assert (found["pet_species"], found["pet_breed"]) == ("dog", "Beagle")


@spec("observability-api", "Requests identify the matched pet")
async def test_unmatched_pet_is_null(api, committed, desk):
    async with committed() as s:
        request = BookingRequest(
            facility_id=desk.facility_id, owner_id=desk.owner_id, raw_message="Hello?"
        )
        s.add(request)
        await s.commit()

    [row] = (await api.get("/requests")).json()
    detail = (await api.get(f"/requests/{request.id}")).json()

    for found in (row, detail):
        assert [found[k] for k in ("pet", "pet_id", "pet_species", "pet_breed")] == [None] * 4


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
    records = [r["benchmark"] for r in reports if r["kind"] == "records"]
    assert records[:2] == ["v1", "v2"]  # the first report predates versioning


# --- Run progress streams as server-sent events -----------------------------------------


def parse_events(text: str) -> list[tuple[str, dict]]:
    events = []
    for block in text.strip().split("\n\n"):
        fields = dict(line.split(": ", 1) for line in block.splitlines())
        events.append((fields["event"], json.loads(fields["data"])))
    return events


@pytest.fixture
def fast_stream():
    app.dependency_overrides[get_stream_timing] = lambda: StreamTiming(0.02, 10.0)
    yield


@spec("observability-api", "Run progress streams as server-sent events")
async def test_progress_then_end(api, committed, desk, tracer, fast_stream):
    async with committed() as s:
        request = BookingRequest(
            facility_id=desk.facility_id, owner_id=desk.owner_id, raw_message="Can Biscuit board?"
        )
        s.add(request)
        await s.flush()
        await attach_certificate(s, request.id, PNG)
        await s.commit()
    settings = fake_settings()

    async def process():
        await asyncio.sleep(0.1)  # let the stream open first
        await process_request(
            request.id,
            sessions=committed,
            tracer=tracer,
            today=TODAY,
            client=make_client(settings, transport=httpx.MockTransport(FakeModel(delay=0.2))),
            settings=settings,
            policy=RetryPolicy(max_attempts=1),
        )

    response, _ = await asyncio.gather(api.get(f"/requests/{request.id}/events"), process())

    assert response.headers["content-type"].startswith("text/event-stream")
    events = parse_events(response.text)
    snapshots = [data for kind, data in events if kind == "snapshot"]
    assert events[-1][0] == "end"
    assert snapshots[0]["status"] == "received"
    assert any(any(s["status"] == "running" for s in snap["spans"]) for snap in snapshots)
    assert snapshots[-1]["status"] == "sent"
    assert "input" not in snapshots[-1]["spans"][0]  # light snapshots, no payloads


@spec("observability-api", "Run progress streams as server-sent events")
async def test_resting_request_gets_one_snapshot(api, run, fast_stream):
    request_id = await run()

    events = parse_events((await api.get(f"/requests/{request_id}/events")).text)

    assert [kind for kind, _ in events] == ["snapshot", "end"]
    assert (events[0][1]["status"], events[0][1]["flagged"]) == ("sent", False)
    assert events[0][1]["failed_step"] is None


async def test_events_for_unknown_request_is_404(api):
    response = await api.get("/requests/00000000-0000-0000-0000-000000000000/events")

    assert response.status_code == 404


# --- Demo requests run in the background ------------------------------------------------


@pytest.fixture
async def demo_owner(committed, desk):
    """Give the test owner the injection sample's seeded email address."""
    async with committed() as s:
        owner = await s.get(Owner, desk.owner_id)
        owner.email = SAMPLES["injection"].owner_email
        await s.commit()


@pytest.fixture
def scripted_background():
    settings = fake_settings()
    app.dependency_overrides[get_llm_kwargs] = lambda: {
        "client": make_client(settings, transport=httpx.MockTransport(FakeModel())),
        "settings": settings,
        "policy": RetryPolicy(max_attempts=1),
    }
    yield


async def wait_for(committed, request_id, states, seconds=5.0):
    for _ in range(int(seconds / 0.05)):
        async with committed() as s:
            status = (await s.get(BookingRequest, request_id)).status
        if status in states:
            return status
        await asyncio.sleep(0.05)
    return status


@spec("observability-api", "Demo requests run in the background")
async def test_samples_include_an_injection_attempt(api):
    samples = (await api.get("/demo/samples")).json()

    injection = next(s for s in samples if s["id"] == "injection")
    assert "ignore your rules" in injection["message"]


@spec("observability-api", "Demo requests run in the background")
async def test_submit_the_injection_sample(api, committed, demo_owner, scripted_background):
    response = await api.post("/demo/requests", json={"sample": "injection"})

    assert response.status_code == 202
    request_id = uuid.UUID(response.json()["id"])
    status = await wait_for(committed, request_id, {"needs_review", "sent", "failed"})
    assert status == "needs_review"
    async with committed() as s:
        request = await s.get(BookingRequest, request_id)
    assert "ignore your rules" in request.raw_message


@spec("observability-api", "Demo requests run in the background")
async def test_unknown_sample(api, committed, demo_owner):
    response = await api.post("/demo/requests", json={"sample": "no-such-sample"})

    assert response.status_code == 404
    async with committed() as s:
        assert await s.scalar(select(func.count()).select_from(BookingRequest)) == 0
