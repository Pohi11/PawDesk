"""ORM models. Importing this package registers every table on Base.metadata."""

from app.models.base import Base
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
    "Base",
    "Facility",
    "Kennel",
    "Owner",
    "Pet",
    "Reservation",
    "VaccineRecord",
    "VaccineRule",
]
