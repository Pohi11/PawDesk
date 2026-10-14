"""Spec: booking-domain, facility-local calendar dates (decision record 0005)."""

from datetime import UTC, date, datetime

import pytest

from app.dates import facility_date

spec = pytest.mark.spec


@spec("booking-domain", "Instants convert to the facility's calendar date")
def test_late_evening_in_chicago_is_still_the_previous_day():
    instant = datetime(2027, 3, 7, 3, 30, tzinfo=UTC)

    assert facility_date("America/Chicago", instant) == date(2027, 3, 6)


@spec("booking-domain", "Instants convert to the facility's calendar date")
def test_ahead_of_utc_facility_is_already_the_next_day():
    instant = datetime(2027, 3, 6, 20, 0, tzinfo=UTC)

    assert facility_date("Asia/Tokyo", instant) == date(2027, 3, 7)


@spec("booking-domain", "Instants convert to the facility's calendar date")
def test_naive_datetime_is_rejected():
    with pytest.raises(ValueError, match="timezone-aware"):
        facility_date("America/Chicago", datetime(2027, 3, 6, 12, 0))
