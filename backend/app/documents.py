"""Certificate images attached to booking requests (spec: booking-domain, design D5)."""

import hashlib
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BookingDocument
from app.records import MAX_IMAGE_BYTES, sniff_image_type


class UnsupportedDocument(ValueError):
    """The file is not a PNG, JPEG, or WebP image of at most 5 MB. Nothing was stored."""


async def attach_certificate(
    session: AsyncSession, booking_request_id: uuid.UUID, image: bytes
) -> BookingDocument:
    """Store `image` for the request. Checked before anything is written; the type comes
    from the file's magic bytes, never its name. A second certificate for the same request
    fails on the unique constraint. The caller owns the commit."""
    if not image:
        raise UnsupportedDocument("empty file")
    if len(image) > MAX_IMAGE_BYTES:
        raise UnsupportedDocument(f"file larger than {MAX_IMAGE_BYTES // (1024 * 1024)} MB")
    mime = sniff_image_type(image)
    if mime is None:
        raise UnsupportedDocument("unsupported file type (PNG, JPEG, or WebP only)")

    document = BookingDocument(
        booking_request_id=booking_request_id,
        mime=mime,
        sha256=hashlib.sha256(image).hexdigest(),
        size_bytes=len(image),
        content=image,
    )
    session.add(document)
    await session.flush()
    return document


async def load_certificate(
    session: AsyncSession, booking_request_id: uuid.UUID
) -> BookingDocument | None:
    return await session.scalar(
        select(BookingDocument).where(BookingDocument.booking_request_id == booking_request_id)
    )
