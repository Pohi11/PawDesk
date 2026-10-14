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
from app.models.orchestration import BookingDocument, BookingStepResult
from app.models.tracing import Span, Trace

__all__ = [
    "Approval",
    "Base",
    "BookingDocument",
    "BookingRequest",
    "BookingStepResult",
    "BookingTransition",
    "Facility",
    "Kennel",
    "Owner",
    "Pet",
    "Reservation",
    "Span",
    "Trace",
    "VaccineRecord",
    "VaccineRule",
]
