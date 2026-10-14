"""Kennel capacity (spec: kennel-capacity, design D6, decision record 0005)."""

import uuid
from datetime import date

from sqlalchemy import Date, exists, func, literal, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import SizeClass
from app.models import Kennel, Reservation

# Half-open bounds: a stay's nights are [start, end), the same ranges the reservations
# exclusion constraint compares, so this search and the constraint agree on "overlap".
NIGHTS = literal_column("'[)'")


async def find_kennel(
    session: AsyncSession, facility_id: uuid.UUID, size_class: SizeClass, start: date, end: date
) -> Kennel | None:
    """The first free kennel (by name) of exactly `size_class` for every night of the stay.

    Advisory only: another transaction can take the kennel before it is reserved. The
    exclusion constraint on reservations remains the real guarantee against double-booking.
    """
    if end <= start:
        raise ValueError(f"a stay needs at least one night (got {start} to {end})")

    stay = func.daterange(literal(start, Date), literal(end, Date), NIGHTS)
    booked = select(Reservation.id).where(
        Reservation.kennel_id == Kennel.id,  # correlated to the outer kennel row
        func.daterange(Reservation.start_date, Reservation.end_date, NIGHTS).op("&&")(stay),
    )
    return await session.scalar(
        select(Kennel)
        .where(
            Kennel.facility_id == facility_id,
            Kennel.size_class == size_class,
            ~exists(booked),
        )
        .order_by(Kennel.name)
        .limit(1)
    )
