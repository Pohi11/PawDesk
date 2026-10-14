"""What the orchestrator stores per request: the certificate image and each step's result
(spec: booking-orchestration, booking-domain; design D2, D5)."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.enums import Step
from app.models.base import Base, UUIDPrimaryKey
from app.models.types import created_at_column, str_enum

# Same limits the records step enforces (app.records); repeated here as a database backstop.
MAX_DOCUMENT_BYTES = 5 * 1024 * 1024
DOCUMENT_TYPES = ("image/png", "image/jpeg", "image/webp")


class BookingDocument(UUIDPrimaryKey, Base):
    """The certificate image sent with a request. One per request (design D5)."""

    __tablename__ = "booking_documents"
    __table_args__ = (
        CheckConstraint(
            f"mime IN ({', '.join(repr(t) for t in DOCUMENT_TYPES)})", name="supported_type"
        ),
        CheckConstraint(
            f"size_bytes > 0 AND size_bytes <= {MAX_DOCUMENT_BYTES}", name="size_in_range"
        ),
        CheckConstraint("size_bytes = octet_length(content)", name="size_matches_content"),
        CheckConstraint("sha256 ~ '^[0-9a-f]{64}$'", name="sha256_is_hex"),
    )

    booking_request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("booking_requests.id"), unique=True
    )
    mime: Mapped[str] = mapped_column(String(32))
    sha256: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(Integer)
    content: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = created_at_column()


class BookingStepResult(UUIDPrimaryKey, Base):
    """A finished step's output: the checkpoint a resumed run reads instead of redoing the
    step. The unique pair makes a second result for the same step impossible (design D2)."""

    __tablename__ = "booking_step_results"
    __table_args__ = (
        UniqueConstraint("booking_request_id", "step"),
        CheckConstraint("jsonb_typeof(output) = 'object'", name="output_is_object"),
    )

    booking_request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("booking_requests.id"))
    step: Mapped[Step] = mapped_column(str_enum(Step, "step"))
    output: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = created_at_column()


class OutboundMessage(UUIDPrimaryKey, Base):
    """The message sent for a request: the reply, or a decline. Recorded, not delivered
    (no email integration yet). One per request, so a retried send can't send twice."""

    __tablename__ = "outbound_messages"
    __table_args__ = (
        CheckConstraint("kind IN ('reply', 'decline')", name="kind_known"),
        CheckConstraint("btrim(body) <> ''", name="body_not_blank"),
    )

    booking_request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("booking_requests.id"), unique=True
    )
    kind: Mapped[str] = mapped_column(String(16))
    subject: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_column()
