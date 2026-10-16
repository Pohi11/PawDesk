"""Spec: observability-api, through the FastAPI app against a real database."""

import asyncio
import io
import json
import uuid
from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest
from PIL import Image
from sqlalchemy import func, select

from app.api import (
    StreamTiming,
    get_demo_limits,
    get_llm_kwargs,
    get_results_dir,
    get_stream_timing,
)
from app.capacity import find_kennel
from app.certificate_card import render
from app.db import get_sessionmaker
from app.demo import DEMO_TODAY, SAMPLE_CARDS, SAMPLES, submit_sample
from app.documents import attach_certificate, load_certificate
from app.enums import SizeClass, SpanKind, Species
from app.intake import match_pet
from app.limits import DemoLimits
from app.llm import RetryPolicy, make_client
from app.main import app
from app.models import BookingRequest, Kennel, Owner, Pet, Reservation, Span, Trace
from app.orchestrator import process_request
from scripts.draw_sample_cards import CARDS
from scripts.seed import seed
from tests.test_llm import fake_settings
from tests.test_orchestrator import (
    CERTIFICATE,
    CLEAR_STATES,
    EN_DASH_PROPOSAL,
    EN_DASH_SUMMARY,
    INTENT,
    ONE_DAY_REPLY,
    PNG,
    START,
    TODAY,
    FakeModel,
    fill_kennel,
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


# --- JSON responses declare UTF-8 -----------------------------------------------------


@spec("observability-api", "JSON responses declare UTF-8")
async def test_non_ascii_text_in_a_response(api, run, committed, desk):
    await fill_kennel(committed, desk)
    request_id = await run(FakeModel(resolver=EN_DASH_PROPOSAL))

    response = await api.get(f"/requests/{request_id}")

    assert response.headers["content-type"] == "application/json; charset=utf-8"
    assert "–".encode() in response.content  # sent as UTF-8, not escaped
    assert response.json()["steps"]["resolution"]["proposal"]["summary"] == EN_DASH_SUMMARY


@spec("observability-api", "JSON responses declare UTF-8")
async def test_error_responses_declare_utf8_too(api):
    unknown = await api.get("/requests/00000000-0000-0000-0000-000000000000")
    invalid = await api.post("/demo/requests", json={"sample": "clean", "seed": 1})

    assert (unknown.status_code, invalid.status_code) == (404, 422)
    assert unknown.headers["content-type"] == "application/json; charset=utf-8"
    assert invalid.headers["content-type"] == "application/json; charset=utf-8"


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


# --- Generated demo requests (spec: demo-generator) -------------------------------------


@pytest.fixture
async def full_seed(committed):
    async with committed() as s:
        await seed(s, DEMO_TODAY)
        await s.commit()


@spec("demo-generator", "Certificates can be viewed before sending")
async def test_generated_preview_and_image(api, full_seed):
    preview = (await api.get("/demo/generate", params={"seed": 42})).json()
    image = await api.get(preview["certificate_url"])

    assert preview["seed"] == 42 and preview["pet"] in preview["message"]
    assert preview["scenario"] in {"current", "expired", "expires_during_stay", "missing"}
    assert (image.status_code, image.headers["content-type"]) == (200, "image/png")
    assert image.content.startswith(b"\x89PNG")
    random_seed = (await api.get("/demo/generate")).json()["seed"]
    assert isinstance(random_seed, int)


@spec("demo-generator", "Certificates can be viewed before sending")
async def test_sample_certificates(api):
    with_card = await api.get("/demo/samples/clean/certificate.png")
    without = await api.get("/demo/samples/unknown-pet/certificate.png")
    unknown = await api.get("/demo/samples/no-such/certificate.png")

    assert (with_card.status_code, with_card.headers["content-type"]) == (200, "image/png")
    assert (without.status_code, unknown.status_code) == (404, 404)


@spec("demo-generator", "A generated request runs like a sample")
@spec("demo-generator", "Certificates can be viewed before sending")
async def test_send_a_generated_request(api, committed, full_seed, scripted_background):
    preview = (await api.get("/demo/generate", params={"seed": 42})).json()
    image = (await api.get(preview["certificate_url"])).content

    response = await api.post("/demo/requests", json={"seed": 42})

    assert response.status_code == 202
    request_id = uuid.UUID(response.json()["id"])
    status = await wait_for(committed, request_id, {"needs_review", "sent", "failed", "drafting"})
    assert status != "received"  # it was processed in the background
    async with committed() as s:
        request = await s.get(BookingRequest, request_id)
        owner = await s.get(Owner, request.owner_id)
        stored = await load_certificate(s, request_id)
    assert request.raw_message == preview["message"]
    assert owner.full_name == preview["owner"]
    assert stored.content == image  # the same card that was previewed


@spec("demo-generator", "Generated pets are new")
async def test_sending_adds_the_pet_once(api, committed, full_seed, scripted_background):
    preview = (await api.get("/demo/generate", params={"seed": 42})).json()

    ids = [
        uuid.UUID((await api.post("/demo/requests", json={"seed": 42})).json()["id"])
        for _ in range(2)
    ]

    for request_id in ids:
        await wait_for(committed, request_id, {"needs_review", "sent", "failed", "drafting"})
    async with committed() as s:
        owner_ids = {(await s.get(BookingRequest, i)).owner_id for i in ids}
        pets = list(await s.scalars(select(Pet).where(Pet.name == preview["pet"])))
        owners_pets = list(await s.scalars(select(Pet).where(Pet.owner_id.in_(owner_ids))))
    assert len(owner_ids) == 1 and len(pets) == 1
    (pet,) = pets
    assert (str(pet.species), pet.breed, pet.weight_lb) == (
        preview["species"],
        preview["breed"],
        Decimal(str(preview["weight_lb"])),
    )
    assert match_pet(preview["pet"], owners_pets) == (pet.id, None)  # intake finds one pet


@spec("demo-generator", "New names avoid names in use")
async def test_generated_names_avoid_pets_on_file_and_recent_names(api, committed, full_seed):
    sent = (await api.get("/demo/generate", params={"seed": 42})).json()["pet"]
    async with committed() as s:
        owner_id = await s.scalar(select(Owner.id).limit(1))
        s.add(Pet(owner_id=owner_id, name=sent, species=Species.DOG, weight_lb=Decimal(30)))
        await s.commit()
    recent = ["Pickle", "Maple", "Miso", "Cleo", "Luna"]

    names = [
        (await api.get("/demo/generate", params={"avoid": recent})).json()["pet"] for _ in range(25)
    ]

    assert not {n.casefold() for n in names} & {n.casefold() for n in [sent, *recent]}
    kept = await api.get("/demo/generate", params={"seed": 42, "avoid": [sent]})
    assert kept.json()["pet"] == sent  # a given seed is used as is


@spec("demo-generator", "Previews carry their pet's photo fields")
async def test_samples_carry_their_pets_photo_fields(api, committed, full_seed):
    samples = {s["id"]: s for s in (await api.get("/demo/samples")).json()}

    async with committed() as s:
        biscuit = await s.scalar(select(Pet).where(Pet.name == "Biscuit"))
    clean, unknown = samples["clean"], samples["unknown-pet"]
    assert (clean["pet"], clean["pet_id"], clean["pet_species"], clean["pet_breed"]) == (
        "Biscuit",
        str(biscuit.id),
        "dog",
        "Beagle",
    )
    assert (unknown["pet_id"], unknown["pet_species"], unknown["pet_breed"]) == (None, None, None)


@spec("demo-generator", "Samples carry a request summary")
async def test_samples_carry_a_request_summary(api, committed, full_seed):
    samples = {s["id"]: s for s in (await api.get("/demo/samples")).json()}

    async with committed() as s:
        biscuit = await s.scalar(select(Pet).where(Pet.name == "Biscuit"))
        avery = await s.scalar(select(Owner).where(Owner.id == biscuit.owner_id))
    clean, unknown = samples["clean"], samples["unknown-pet"]
    assert clean["service"] == "boarding"
    assert (clean["start_date"], clean["end_date"]) == ("2027-03-24", "2027-03-27")
    assert (clean["owner"], clean["weight_lb"]) == (avery.full_name, float(biscuit.weight_lb))
    assert clean["card_text"] == "Every vaccine on the card is current for the whole stay."

    assert (unknown["pet"], unknown["service"]) == ("Rex", "daycare")
    assert (unknown["start_date"], unknown["end_date"]) == ("2027-03-15", "2027-03-15")
    assert unknown["owner"] and unknown["weight_lb"] is None
    assert "no vaccine card is attached" in unknown["card_text"]


@spec("demo-generator", "Samples carry a request summary")
@pytest.mark.parametrize("sample_id", sorted(CARDS))
def test_sample_dates_match_their_card(sample_id):
    record = CARDS[sample_id][1]()
    sample = SAMPLES[sample_id]
    assert (sample.service, sample.start_date, sample.end_date) == (
        record.service,
        record.start_date,
        record.end_date,
    )


@spec("observability-api", "Each sample is about a different pet")
async def test_no_two_samples_share_a_pet(api, committed, full_seed):
    samples = (await api.get("/demo/samples")).json()

    pet_ids = [s["pet_id"] for s in samples if s["pet_id"] is not None]
    assert len(pet_ids) == len(set(pet_ids)) >= 3


@spec("observability-api", "Each sample is about a different pet")
async def test_the_injection_samples_card_is_the_same_each_time(api):
    first = await api.get("/demo/samples/injection/certificate.png")
    second = await api.get("/demo/samples/injection/certificate.png")

    assert first.status_code == 200 and first.content.startswith(b"\x89PNG")
    assert first.content == second.content


@spec("observability-api", "Each sample is about a different pet")
@pytest.mark.parametrize("sample_id", sorted(CARDS))
async def test_each_samples_card_is_served_as_committed(api, sample_id):
    served = await api.get(f"/demo/samples/{sample_id}/certificate.png")

    file, _ = CARDS[sample_id]
    assert SAMPLES[sample_id].certificate == file
    assert served.content == (SAMPLE_CARDS / file).read_bytes()


@spec("observability-api", "Each sample is about a different pet")
@pytest.mark.parametrize("sample_id", sorted(CARDS))
async def test_each_committed_card_matches_a_fresh_drawing(committed, full_seed, sample_id):
    file, request = CARDS[sample_id]
    record = request()

    # About the sample's pet, printed with its owner on file's initial and surname.
    sample = SAMPLES[sample_id]
    async with committed() as session:
        owner = await session.scalar(select(Owner).where(Owner.email == sample.owner_email))
    first, *_, last = owner.full_name.split()
    assert (record.pet, record.owner_email, record.owner) == (
        sample.pet,
        sample.owner_email,
        f"{first[0]}. {last}",
    )

    # Pixels, not bytes: the PNG compressor differs by platform, the drawing does not.
    stored = Image.open(SAMPLE_CARDS / file)
    drawn = Image.open(io.BytesIO(render(record)))
    assert stored.size == drawn.size
    assert stored.tobytes() == drawn.tobytes(), "redraw: uv run python -m scripts.draw_sample_cards"


@spec("observability-api", "Each sample is about a different pet")
@pytest.mark.parametrize("sample_id", sorted(CARDS))
def test_no_card_shows_a_shot_from_the_future(sample_id):
    # The real date, not DEMO_TODAY: visitors read the card today, whatever date the demo runs on.
    record = CARDS[sample_id][1]()
    future = [r.label for r in record.records if r.administered_on > date.today()]
    assert not future, f"{sample_id}: given after today: {future}"


@spec("demo-generator", "Previews carry their pet's photo fields")
async def test_the_seed_fixes_the_pet_id(api, committed, full_seed, scripted_background):
    first = (await api.get("/demo/generate", params={"seed": 42})).json()
    second = (await api.get("/demo/generate", params={"seed": 42})).json()

    request_id = uuid.UUID((await api.post("/demo/requests", json={"seed": 42})).json()["id"])

    await wait_for(committed, request_id, {"needs_review", "sent", "failed", "drafting"})
    async with committed() as s:
        pet = await s.get(Pet, uuid.UUID(first["pet_id"]))
    assert first["pet_id"] == second["pet_id"]
    assert pet is not None and pet.name == first["pet"]


async def test_too_many_recent_names_are_refused(api):
    response = await api.get("/demo/generate", params={"avoid": [f"n{i}" for i in range(21)]})

    assert response.status_code == 422


async def test_sample_and_seed_together_are_refused(api):
    response = await api.post("/demo/requests", json={"sample": "clean", "seed": 1})

    assert response.status_code == 422


# --- Model-use limits for the public demo (spec: demo-hosting) --------------------------

LIMITS = "Model use is capped per hour and per day"


@pytest.fixture
def limits():
    def set_limits(per_hour=None, per_day=None):
        app.dependency_overrides[get_demo_limits] = lambda: DemoLimits(per_hour, per_day)

    return set_limits


async def record_spans(committed, kind, count, hours_ago):
    """Record `count` spans of `kind` that started `hours_ago` hours before now."""
    async with committed() as s:
        trace = Trace(name="earlier run")
        s.add(trace)
        await s.flush()
        started = (await s.scalar(select(func.now()))) - timedelta(hours=hours_ago)
        s.add_all(
            Span(trace_id=trace.id, kind=kind, name=f"{kind} call", started_at=started)
            for _ in range(count)
        )
        await s.commit()


async def stored_requests(committed):
    async with committed() as s:
        return await s.scalar(select(func.count()).select_from(BookingRequest))


@spec("demo-hosting", LIMITS)
async def test_hourly_limit_reached(api, committed, demo_owner, limits):
    limits(per_hour=3)
    await record_spans(committed, SpanKind.LLM, 3, hours_ago=0.5)

    response = await api.post("/demo/requests", json={"sample": "injection"})

    assert response.status_code == 429
    assert response.json()["detail"] == (
        "The demo reached its hourly limit on model calls. Try again later."
    )
    assert await stored_requests(committed) == 0


@spec("demo-hosting", LIMITS)
async def test_daily_limit_reached(api, committed, demo_owner, limits):
    limits(per_hour=3, per_day=5)
    await record_spans(committed, SpanKind.LLM, 5, hours_ago=2)

    response = await api.post("/demo/requests", json={"seed": 42})

    assert response.status_code == 429
    assert "daily limit" in response.json()["detail"]
    assert await stored_requests(committed) == 0


@spec("demo-hosting", LIMITS)
async def test_only_recent_model_calls_count(
    api, committed, demo_owner, limits, scripted_background
):
    limits(per_hour=3)
    await record_spans(committed, SpanKind.LLM, 3, hours_ago=1.5)
    await record_spans(committed, SpanKind.TOOL, 3, hours_ago=0.1)
    await record_spans(committed, SpanKind.CODE, 3, hours_ago=0.1)

    response = await api.post("/demo/requests", json={"sample": "injection"})

    assert response.status_code == 202
    await wait_for(committed, uuid.UUID(response.json()["id"]), {"needs_review", "sent", "failed"})


@spec("demo-hosting", LIMITS)
async def test_no_limit_configured(api, committed, demo_owner, limits, scripted_background):
    limits()
    await record_spans(committed, SpanKind.LLM, 50, hours_ago=0.1)

    response = await api.post("/demo/requests", json={"sample": "injection"})

    assert response.status_code == 202
    await wait_for(committed, uuid.UUID(response.json()["id"]), {"needs_review", "sent", "failed"})


# --- Running a boarding sample frees its stay ------------------------------------------


async def hold(committed, kennel_name, start, end, *, by_request=True):
    """Reserve a kennel for a fresh dog, made by a request unless `by_request` is False."""
    async with committed() as s:
        kennel = await s.scalar(select(Kennel).where(Kennel.name == kennel_name))
        owner = await s.scalar(select(Owner).order_by(Owner.email).limit(1))
        guest = Pet(owner_id=owner.id, name="Guest", species=Species.DOG, weight_lb=Decimal(30))
        s.add(guest)
        await s.flush()
        request_id = None
        if by_request:
            request = BookingRequest(
                facility_id=kennel.facility_id, owner_id=owner.id, raw_message="earlier"
            )
            s.add(request)
            await s.flush()
            request_id = request.id
        reservation = Reservation(
            kennel_id=kennel.id,
            pet_id=guest.id,
            booking_request_id=request_id,
            start_date=start,
            end_date=end,
        )
        s.add(reservation)
        await s.commit()
        return reservation.id


async def reservations_left(committed, ids):
    async with committed() as s:
        return set(await s.scalars(select(Reservation.id).where(Reservation.id.in_(ids))))


CLEAN = SAMPLES["clean"]


@spec("observability-api", "Running a boarding sample frees its stay")
async def test_earlier_runs_filled_the_kennels(committed, full_seed):
    held = [await hold(committed, k, CLEAN.start_date, CLEAN.end_date) for k in ("M1", "M2", "M3")]

    request_id = await submit_sample(committed, "clean")

    async with committed() as s:
        facility_id = (await s.get(BookingRequest, request_id)).facility_id
        kennel = await find_kennel(
            s, facility_id, SizeClass.MEDIUM, CLEAN.start_date, CLEAN.end_date
        )
    assert await reservations_left(committed, held) == set()
    assert kennel is not None


@spec("observability-api", "Running a boarding sample frees its stay")
async def test_seeded_reservations_stay(committed, full_seed):
    seeded = await hold(
        committed, "M1", CLEAN.start_date, CLEAN.start_date + timedelta(days=1), by_request=False
    )

    await submit_sample(committed, "clean")

    assert await reservations_left(committed, [seeded]) == {seeded}


@spec("observability-api", "Running a boarding sample frees its stay")
async def test_other_stays_stay(committed, full_seed):
    later = await hold(
        committed, "M1", CLEAN.end_date + timedelta(days=1), CLEAN.end_date + timedelta(days=3)
    )
    large = await hold(committed, "L1", CLEAN.start_date, CLEAN.end_date)

    await submit_sample(committed, "clean")

    assert await reservations_left(committed, [later, large]) == {later, large}


@spec("observability-api", "Running a boarding sample frees its stay")
async def test_non_boarding_samples_release_nothing(committed, full_seed):
    held = await hold(committed, "M1", date(2027, 3, 15), date(2027, 3, 16))

    await submit_sample(committed, "unknown-pet")  # daycare on Mar 15

    assert await reservations_left(committed, [held]) == {held}
