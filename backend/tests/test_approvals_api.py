"""Spec: staff-approval, through the FastAPI app against a real database."""

import httpx
import pytest
from sqlalchemy import func, select

from app.db import get_sessionmaker
from app.enums import Step
from app.lifecycle import Actor, State
from app.main import app
from app.models import Approval, BookingRequest, BookingStepResult, OutboundMessage
from app.transitions import transition

spec = pytest.mark.spec

DRAFT = {"subject": "Biscuit's stay", "body": "Hi Test, would March 14 to 17 work instead?"}
FACTS = {
    "owner_first_name": "Test",
    "pet_name": "Biscuit",
    "facility": "Test Lodge",
    "service": "boarding",
    "start_date": "2027-03-10",
    "end_date": "2027-03-13",
    "situation": "alternatives",
    "options": [],
    "vaccines_needed": [],
}
FLAGS = ["came through resolving: proposed (proposed)"]


@pytest.fixture
async def api(committed):
    app.dependency_overrides[get_sessionmaker] = lambda: committed
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def flagged(committed, desk):
    """A request paused in needs_review with a saved draft, as the orchestrator leaves it."""

    async def make(state_path=(State.RESOLVING, State.DRAFTING, State.NEEDS_REVIEW)):
        async with committed() as s:
            request = BookingRequest(
                facility_id=desk.facility_id,
                owner_id=desk.owner_id,
                pet_id=desk.biscuit_id,
                raw_message="Can Biscuit board?",
            )
            s.add(request)
            await s.flush()
            for target in (State.EXTRACTING, State.CHECKING, *state_path):
                await transition(s, request, target, Actor.SYSTEM)
            s.add_all(
                [
                    BookingStepResult(
                        booking_request_id=request.id,
                        step=Step.INTAKE,
                        output={"intent": {"service": "boarding", "start_date": "2027-03-10"}},
                    ),
                    BookingStepResult(
                        booking_request_id=request.id,
                        step=Step.REPLY,
                        output={
                            "situation": "alternatives",
                            "facts": FACTS,
                            "draft": DRAFT,
                            "flags": FLAGS,
                        },
                    ),
                ]
            )
            await s.commit()
            return request.id

    return make


async def message_for(committed, request_id) -> OutboundMessage | None:
    async with committed() as s:
        return await s.scalar(
            select(OutboundMessage).where(OutboundMessage.booking_request_id == request_id)
        )


async def approvals_for(committed, request_id) -> list[Approval]:
    async with committed() as s:
        rows = await s.scalars(select(Approval).where(Approval.booking_request_id == request_id))
        return list(rows)


async def status_of(committed, request_id) -> State:
    async with committed() as s:
        return (await s.get(BookingRequest, request_id)).status


@spec("staff-approval", "Staff can see the review queue")
async def test_queue_lists_only_waiting_requests(api, committed, flagged):
    waiting = await flagged()
    done = await flagged()
    await api.post(f"/requests/{done}/approve", json={"staff_name": "Sam"})

    response = await api.get("/reviews")

    assert response.status_code == 200
    [entry] = response.json()
    assert entry["id"] == str(waiting)
    assert (entry["owner"], entry["pet"], entry["service"]) == ("Test Owner", "Biscuit", "boarding")
    assert (entry["flags"], entry["draft"]) == (FLAGS, DRAFT)


@spec("staff-approval", "Staff decide flagged requests")
async def test_approve(api, committed, flagged):
    request_id = await flagged()

    response = await api.post(f"/requests/{request_id}/approve", json={"staff_name": "Sam"})

    assert (response.status_code, response.json()) == (200, {"status": "sent"})
    [approval] = await approvals_for(committed, request_id)
    assert (approval.action, approval.staff_name) == ("approve", "Sam")
    message = await message_for(committed, request_id)
    assert (message.kind, message.body) == ("reply", DRAFT["body"])


@spec("staff-approval", "Staff decide flagged requests")
async def test_edit_and_approve(api, committed, flagged):
    request_id = await flagged()
    edited = "Hi Test, March 14 to 17 works for us if it suits you. The Test Lodge team"

    response = await api.post(
        f"/requests/{request_id}/edit-and-approve", json={"staff_name": "Sam", "reply": edited}
    )

    assert response.json() == {"status": "sent"}
    assert (await message_for(committed, request_id)).body == edited
    [approval] = await approvals_for(committed, request_id)
    assert approval.edited_reply == edited


@spec("staff-approval", "Staff decide flagged requests")
async def test_reject_with_a_reason(api, committed, flagged):
    request_id = await flagged()

    response = await api.post(
        f"/requests/{request_id}/reject",
        json={"staff_name": "Sam", "reason": "Owner owes for the last stay"},
    )

    assert response.json() == {"status": "sent"}
    message = await message_for(committed, request_id)
    assert message.kind == "decline"
    assert message.body.startswith("Hi Test,")
    assert "owes" not in message.body  # the internal reason is never sent
    [approval] = await approvals_for(committed, request_id)
    assert approval.reason == "Owner owes for the last stay"


@spec("staff-approval", "Staff decide flagged requests")
@pytest.mark.parametrize("reason", ["", "   "])
async def test_reject_without_a_reason(api, committed, flagged, reason):
    request_id = await flagged()

    response = await api.post(
        f"/requests/{request_id}/reject", json={"staff_name": "Sam", "reason": reason}
    )

    assert response.status_code == 422
    assert await status_of(committed, request_id) == State.NEEDS_REVIEW
    assert await approvals_for(committed, request_id) == []


@spec("staff-approval", "Staff decide flagged requests")
async def test_acting_twice(api, committed, flagged):
    request_id = await flagged()
    await api.post(f"/requests/{request_id}/approve", json={"staff_name": "Sam"})

    again = await api.post(f"/requests/{request_id}/approve", json={"staff_name": "Alex"})

    assert again.status_code == 409
    assert len(await approvals_for(committed, request_id)) == 1


@spec("staff-approval", "Staff decide flagged requests")
async def test_request_that_was_never_flagged_is_refused(api, committed, flagged):
    request_id = await flagged(state_path=(State.DRAFTING, State.READY))

    response = await api.post(f"/requests/{request_id}/approve", json={"staff_name": "Sam"})

    assert response.status_code == 409
    async with committed() as s:
        count = await s.scalar(select(func.count()).select_from(Approval))
    assert count == 0


async def test_unknown_request_is_404(api):
    response = await api.post(
        "/requests/00000000-0000-0000-0000-000000000000/approve", json={"staff_name": "Sam"}
    )

    assert response.status_code == 404
