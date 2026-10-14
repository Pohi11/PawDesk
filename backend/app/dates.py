"""Turning moments in time into facility calendar dates (decision record 0005)."""

from datetime import date, datetime
from zoneinfo import ZoneInfo


def facility_date(timezone: str, instant: datetime) -> date:
    """The calendar date `instant` falls on in the facility's time zone.

    Naive datetimes are rejected: without a zone there's no way to know which day they mean,
    and guessing (server-local or UTC) is how off-by-one-day bugs start.
    """
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("instant must be timezone-aware")
    return instant.astimezone(ZoneInfo(timezone)).date()
