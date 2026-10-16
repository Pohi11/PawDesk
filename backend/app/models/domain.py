"""Records a facility needs before it can say yes to a booking (spec: booking-domain)."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, ClassVar
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import (
    CheckConstraint,
    Computed,
    Date,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    column,
    func,
)
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.enums import Service, SizeClass, Species, Vaccine
from app.models.base import Base, UUIDPrimaryKey
from app.models.types import created_at_column, str_enum

# The single source of truth for size class (design D4). CASE is evaluated top to bottom
# and the first match wins, so each WHEN only needs the upper bound.
SIZE_CLASS_SQL = """
CASE
    WHEN species = 'cat' THEN 'cat'
    WHEN weight_lb < 20 THEN 'small'
    WHEN weight_lb < 50 THEN 'medium'
    WHEN weight_lb < 90 THEN 'large'
    ELSE 'xlarge'
END
"""


class Facility(UUIDPrimaryKey, Base):
    __tablename__ = "facilities"

    name: Mapped[str] = mapped_column(String(200))
    timezone: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = created_at_column()

    # A CHECK constraint can't consult the IANA time zone database, so this is validated
    # in Python before the row is ever sent (design D10).
    @validates("timezone")
    def _validate_timezone(self, _key: str, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"unknown time zone: {value!r}") from exc
        return value


class Owner(UUIDPrimaryKey, Base):
    __tablename__ = "owners"

    full_name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(320), unique=True)
    phone: Mapped[str | None] = mapped_column(String(32))
    emergency_contact_name: Mapped[str | None] = mapped_column(String(200))
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = created_at_column()


class Pet(UUIDPrimaryKey, Base):
    __tablename__ = "pets"
    __table_args__ = (CheckConstraint("weight_lb > 0", name="weight_positive"),)
    # Fetch size_class via RETURNING on insert *and* update. Without this, an update would
    # leave it expired, and reading an expired attribute is an implicit query that async
    # sessions can't run.
    __mapper_args__: ClassVar[dict[str, Any]] = {"eager_defaults": True}

    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("owners.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    species: Mapped[Species] = mapped_column(str_enum(Species, "species"))
    breed: Mapped[str | None] = mapped_column(String(100))
    weight_lb: Mapped[Decimal] = mapped_column(Numeric(5, 1))
    # GENERATED ALWAYS ... STORED: Postgres computes it on every insert/update and rejects
    # any attempt to write it directly. The ORM reads the value back after a flush.
    size_class: Mapped[SizeClass] = mapped_column(
        String(16), Computed(SIZE_CLASS_SQL, persisted=True)
    )
    birth_date: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_column()


class VaccineRule(UUIDPrimaryKey, Base):
    __tablename__ = "vaccine_rules"
    __table_args__ = (UniqueConstraint("facility_id", "service", "species", "vaccine"),)

    facility_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("facilities.id"))
    service: Mapped[Service] = mapped_column(str_enum(Service, "service"))
    species: Mapped[Species] = mapped_column(str_enum(Species, "species"))
    vaccine: Mapped[Vaccine] = mapped_column(str_enum(Vaccine, "vaccine"))


class VaccineRecord(UUIDPrimaryKey, Base):
    __tablename__ = "vaccine_records"
    # A NULL expires_on makes this CHECK evaluate to NULL, which passes: an unknown expiry
    # is allowed here and judged by the compliance rules (Phase 2), not treated as valid.
    __table_args__ = (
        CheckConstraint("expires_on >= administered_on", name="expiry_not_before_given"),
    )

    pet_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pets.id"), index=True)
    vaccine: Mapped[Vaccine] = mapped_column(str_enum(Vaccine, "vaccine"))
    administered_on: Mapped[date] = mapped_column(Date)
    expires_on: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = created_at_column()


class Kennel(UUIDPrimaryKey, Base):
    __tablename__ = "kennels"
    __table_args__ = (UniqueConstraint("facility_id", "name"),)

    facility_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("facilities.id"))
    name: Mapped[str] = mapped_column(String(50))
    size_class: Mapped[SizeClass] = mapped_column(str_enum(SizeClass, "size_class"))


class Reservation(UUIDPrimaryKey, Base):
    __tablename__ = "reservations"
    __table_args__ = (
        CheckConstraint("end_date > start_date", name="at_least_one_night"),
        # No two reservations for the same kennel may share a night (design D5).
        # '[)' = half-open: includes start_date, excludes end_date (checkout morning).
        ExcludeConstraint(
            ("kennel_id", "="),
            (func.daterange(column("start_date"), column("end_date"), "[)"), "&&"),
            name="ex_reservations_no_overlapping_stays",
            using="gist",
        ),
        # Nor may two reservations for the same pet (change one-kennel-per-pet, D1).
        ExcludeConstraint(
            ("pet_id", "="),
            (func.daterange(column("start_date"), column("end_date"), "[)"), "&&"),
            name="ex_reservations_one_kennel_per_pet",
            using="gist",
        ),
    )

    kennel_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("kennels.id"))
    pet_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pets.id"), index=True)
    # At most one reservation per booking request, so a retried step can't double-book.
    booking_request_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("booking_requests.id"), unique=True
    )
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = created_at_column()
