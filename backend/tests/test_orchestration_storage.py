"""Spec: booking-domain (certificate images) and booking-orchestration (saved step results),
the parts enforced by storage."""

import hashlib

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.documents import UnsupportedDocument, attach_certificate, load_certificate
from app.enums import Step
from app.models import BookingDocument, BookingStepResult
from tests.test_booking_lifecycle import make_request

spec = pytest.mark.spec
PNG = b"\x89PNG\r\n\x1a\n" + b"synthetic certificate pixels " * 50
PDF = b"%PDF-1.7\n" + b"synthetic pdf body " * 50


@spec("booking-domain", "A booking request can carry a certificate image")
async def test_image_round_trips_with_hash_type_and_size(session):
    request = await make_request(session)

    await attach_certificate(session, request.id, PNG)
    session.expunge_all()  # read it back from the database, not the identity map
    stored = await load_certificate(session, request.id)

    assert stored.content == PNG
    assert stored.sha256 == hashlib.sha256(PNG).hexdigest()
    assert (stored.mime, stored.size_bytes) == ("image/png", len(PNG))


@spec("booking-domain", "A booking request can carry a certificate image")
async def test_second_certificate_rejected(session):
    request = await make_request(session)
    await attach_certificate(session, request.id, PNG)

    with pytest.raises(IntegrityError, match="uq_booking_documents_booking_request_id"):
        await attach_certificate(session, request.id, PNG + b"another")


@spec("booking-domain", "A booking request can carry a certificate image")
@pytest.mark.parametrize(
    "data", [PDF, b"", PNG[:8] + b"x" * (5 * 1024 * 1024)], ids=["pdf", "empty", "over-5mb"]
)
async def test_unsupported_file_refused_before_storing(session, data):
    request = await make_request(session)

    with pytest.raises(UnsupportedDocument):
        await attach_certificate(session, request.id, data)

    assert await session.scalar(select(func.count()).select_from(BookingDocument)) == 0


@spec("booking-domain", "A booking request can carry a certificate image")
async def test_database_refuses_a_mismatched_type_even_without_the_check(session):
    request = await make_request(session)
    session.add(
        BookingDocument(
            booking_request_id=request.id,
            mime="application/pdf",
            sha256=hashlib.sha256(PDF).hexdigest(),
            size_bytes=len(PDF),
            content=PDF,
        )
    )
    with pytest.raises(IntegrityError, match="ck_booking_documents_supported_type"):
        await session.flush()


@spec("booking-orchestration", "Each step is saved with its state change")
async def test_one_result_per_step(session):
    request = await make_request(session)
    session.add(BookingStepResult(booking_request_id=request.id, step=Step.INTAKE, output={}))
    await session.flush()

    session.add(BookingStepResult(booking_request_id=request.id, step=Step.INTAKE, output={}))
    with pytest.raises(IntegrityError, match="uq_booking_step_results_booking_request_id_step"):
        await session.flush()


@spec("booking-orchestration", "Each step is saved with its state change")
async def test_step_output_must_be_an_object(session):
    request = await make_request(session)
    session.add(BookingStepResult(booking_request_id=request.id, step=Step.CHECKS, output=[1]))
    with pytest.raises(IntegrityError, match="ck_booking_step_results_output_is_object"):
        await session.flush()
