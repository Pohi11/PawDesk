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
    return await session.scalar(
        select(Kennel)
        .where(
            Kennel.facility_id == facility_id,
            Kennel.size_class == size_class,
            ~_booked(start, end),
        )
        .order_by(Kennel.name)
        .limit(1)
    )


async def free_kennel_counts(
    session: AsyncSession, facility_id: uuid.UUID, start: date, end: date
) -> dict[SizeClass, int]:
    """How many kennels of each size class the facility has free for every night of the
    stay. Size classes the facility has but can't offer appear with 0."""
    free = func.count().filter(~_booked(start, end))
    rows = await session.execute(
        select(Kennel.size_class, free)
        .where(Kennel.facility_id == facility_id)
        .group_by(Kennel.size_class)
    )
    return {SizeClass(size): count for size, count in rows}


def _booked(start: date, end: date):
    """EXISTS a reservation on the outer kennel row that shares a night with the stay."""
    if end <= start:
        raise ValueError(f"a stay needs at least one night (got {start} to {end})")
    stay = func.daterange(literal(start, Date), literal(end, Date), NIGHTS)
    return exists(
        select(Reservation.id).where(
            Reservation.kennel_id == Kennel.id,  # correlated to the outer kennel row
            func.daterange(Reservation.start_date, Reservation.end_date, NIGHTS).op("&&")(stay),
        )
    )
