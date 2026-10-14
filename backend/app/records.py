"""Vaccine records extraction: certificate image -> validated records + issues.

Spec: vaccine-records-extraction. The model reads; code checks dates, labels, and the pet,
and decides when a person must look. Output records use the same `VaccineEvidence` value
the compliance check consumes.
"""

from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.enums import Vaccine

Ambiguity = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Label = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class ExtractedRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: Label = Field(description="The vaccine name exactly as written.")
    vaccine: Vaccine | None = Field(description="Mapped vaccine, or null if none matches.")
    administered_on: date = Field(description="Date given, YYYY-MM-DD.")
    expires_on: date | None = Field(
        description="Printed expiry (last valid day), YYYY-MM-DD; null if not printed."
    )


class CertificateExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pet_name: str | None = Field(description="Pet name as printed, or null.")
    records: list[ExtractedRecord] = Field(max_length=20)
    readable: bool = Field(description="False if the image can't be read reliably.")
    confidence: float = Field(ge=0, le=1, description="How sure you are, from 0 to 1.")
    ambiguities: list[Ambiguity] = Field(max_length=10)
