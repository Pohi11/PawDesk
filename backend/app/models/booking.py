"""Booking requests, their transition log, and staff approvals (spec: booking-lifecycle)."""

import uuid
from datetime import datetime
from typing import Any, ClassVar

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.enums import ApprovalAction
from app.lifecycle import Actor, State
from app.models.base import Base, UUIDPrimaryKey
from app.models.types import created_at_column, str_enum

FAILABLE_STATES = ("extracting", "checking", "resolving", "drafting", "approved", "rejected")


class BookingRequest(UUIDPrimaryKey, Base):
    __tablename__ = "booking_requests"
    __table_args__ = (
        # A failed request always knows where it failed, and nothing else has a failed step
        # (design D8). `=` between two booleans is true only when both sides agree.
        CheckConstraint(
            "(status = 'failed') = (failed_step IS NOT NULL)", name="failed_step_iff_failed"
        ),
        CheckConstraint(
            f"failed_step IN ({', '.join(repr(s) for s in FAILABLE_STATES)})",
            name="failed_step_is_failable",
        ),
    )

    facility_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("facilities.id"))
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("owners.id"))
    # Unknown until the intake step works out which pet the message is about.
    pet_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pets.id"))
    raw_message: Mapped[str] = mapped_column(Text)
    status: Mapped[State] = mapped_column(
        str_enum(State, "status"), default=State.RECEIVED, server_default=State.RECEIVED.value
    )
    failed_step: Mapped[State | None] = mapped_column(str_enum(State, "failed_step"))
    last_error: Mapped[str | None] = mapped_column(Text)
    # Optimistic concurrency (design D7): SQLAlchemy adds `AND version = <loaded>` to every
    # UPDATE and bumps it; if no row matches, someone else changed the request first.
    version: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __mapper_args__: ClassVar[dict[str, Any]] = {"version_id_col": version}


class BookingTransition(UUIDPrimaryKey, Base):
    """One row per successful state change. Written only by app.transitions."""

    __tablename__ = "booking_transitions"

    booking_request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("booking_requests.id"), index=True
    )
    from_status: Mapped[State] = mapped_column(str_enum(State, "from_status"))
    to_status: Mapped[State] = mapped_column(str_enum(State, "to_status"))
    actor: Mapped[Actor] = mapped_column(str_enum(Actor, "actor"))
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_column()


class Approval(UUIDPrimaryKey, Base):
    __tablename__ = "approvals"
    __table_args__ = (
        CheckConstraint(
            "action <> 'reject' OR coalesce(btrim(reason), '') <> ''",
            name="reject_requires_reason",
        ),
    )

    booking_request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("booking_requests.id"), index=True
    )
    action: Mapped[ApprovalAction] = mapped_column(str_enum(ApprovalAction, "action"))
    staff_name: Mapped[str] = mapped_column(String(200))
    reason: Mapped[str | None] = mapped_column(Text)
    edited_reply: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_column()
