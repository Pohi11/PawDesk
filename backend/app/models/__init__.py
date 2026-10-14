"""ORM models. Importing this package registers every table on Base.metadata."""

from app.models.base import Base
from app.models.booking import Approval, BookingRequest, BookingTransition
from app.models.domain import (
    Facility,
    Kennel,
    Owner,
    Pet,
    Reservation,
    VaccineRecord,
    VaccineRule,
)

__all__ = [
    "Approval",
    "Base",
    "BookingRequest",
    "BookingTransition",
    "Facility",
    "Kennel",
    "Owner",
    "Pet",
    "Reservation",
    "VaccineRecord",
    "VaccineRule",
]
