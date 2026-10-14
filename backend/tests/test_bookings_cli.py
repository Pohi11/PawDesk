"""The bookings command line: submitting stores the request and its certificate."""

import hashlib

import pytest

from app.documents import load_certificate
from app.lifecycle import State
from app.models import BookingRequest, Owner
from scripts.bookings import submit
from tests.test_orchestrator import PNG

spec = pytest.mark.spec


@spec("booking-domain", "A booking request can carry a certificate image")
async def test_submit_stores_the_request_and_certificate(committed, desk):
    async with committed() as s:
        email = (await s.get(Owner, desk.owner_id)).email

    request_id = await submit(committed, email, "Can Biscuit board?", PNG)

    async with committed() as s:
        request = await s.get(BookingRequest, request_id)
        document = await load_certificate(s, request_id)
    assert (request.status, request.owner_id, request.facility_id) == (
        State.RECEIVED,
        desk.owner_id,
        desk.facility_id,
    )
    assert document.sha256 == hashlib.sha256(PNG).hexdigest()


async def test_submit_refuses_an_unknown_owner(committed, desk):
    with pytest.raises(SystemExit, match="no owner"):
        await submit(committed, "nobody@example.test", "hi")
