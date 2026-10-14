"""Vaccine records extraction: certificate image -> validated records + issues.

Spec: vaccine-records-extraction. The model reads; code checks dates, labels, and the pet,
and decides when a person must look. Output records use the same `VaccineEvidence` value
the compliance check consumes.
"""

import hashlib
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.compliance import VaccineEvidence
from app.enums import SpanKind, Vaccine
from app.prompts.records import PROMPT_VERSION, build_messages
from app.structured import InvalidModelOutput, extract
from app.tracing import span

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


# --- The pipeline (design D3–D5) ------------------------------------------------------

MAX_IMAGE_BYTES = 5 * 1024 * 1024
CONFIDENCE_THRESHOLD = 0.7


class RecordsOutcome(StrEnum):
    CLEAR = "clear"
    NEEDS_REVIEW = "needs_review"


class RecordsInvalidOutput(InvalidModelOutput):
    """The extraction failed validation, and so did the one repair attempt."""


@dataclass(frozen=True)
class RecordsResult:
    extraction: CertificateExtraction | None
    evidence: tuple[VaccineEvidence, ...]  # only records that map to a known vaccine
    issues: tuple[str, ...]
    outcome: RecordsOutcome


def sniff_image_type(data: bytes) -> str | None:
    """MIME type from the file's magic bytes, never from its name or a client header."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def record_issues(
    extraction: CertificateExtraction, today: date, booked_pet: str | None
) -> list[str]:
    issues = []
    if not extraction.records:
        issues.append("no vaccination records found")
    for r in extraction.records:
        if r.administered_on > today:
            issues.append(f"{r.label!r}: date given {r.administered_on} is after today")
        if r.expires_on is not None and r.expires_on < r.administered_on:
            issues.append(f"{r.label!r}: expiry {r.expires_on} is before the date given")
        if r.vaccine is None:
            issues.append(f"{r.label!r}: not a known vaccine; not used for compliance")
    printed = (extraction.pet_name or "").strip()
    if booked_pet and printed and printed.casefold() != booked_pet.strip().casefold():
        issues.append(f"certificate names {printed!r}, booking is for {booked_pet.strip()!r}")
    if not extraction.readable:
        issues.append("image not readable")
    if extraction.confidence < CONFIDENCE_THRESHOLD:
        issues.append(f"low confidence ({extraction.confidence:.2f})")
    issues += [f"ambiguous: {a}" for a in extraction.ambiguities]
    return issues


def to_evidence(extraction: CertificateExtraction) -> tuple[VaccineEvidence, ...]:
    # Dates pass through exactly as extracted: never adjusted, never filled in (design D3).
    return tuple(
        VaccineEvidence(r.vaccine, r.administered_on, r.expires_on)
        for r in extraction.records
        if r.vaccine is not None
    )


def _refused(issue: str) -> RecordsResult:
    return RecordsResult(None, (), (issue,), RecordsOutcome.NEEDS_REVIEW)


async def run_records(
    image: bytes,
    *,
    booked_pet: str | None,
    today: date,
    timezone: str,
    **llm_kwargs: Any,
) -> RecordsResult:
    """`today` is the facility-local date. `llm_kwargs` pass through to complete()."""
    digest = hashlib.sha256(image).hexdigest()
    async with span(
        "records", SpanKind.CODE, input={"image_sha256": digest, "image_bytes": len(image)}
    ) as s:
        s.attributes.update(prompt_version=PROMPT_VERSION, image_sha256=digest)

        mime = sniff_image_type(image)
        if len(image) > MAX_IMAGE_BYTES:
            result = _refused(
                f"image larger than {MAX_IMAGE_BYTES // (1024 * 1024)} MB; not processed"
            )
        elif mime is None:
            result = _refused("unsupported file type (PNG, JPEG, or WebP only); not processed")
        else:
            extraction, repaired = await extract(
                CertificateExtraction,
                build_messages(image, mime, today, timezone),
                name="records",
                schema_name="vaccine_certificate",
                error_cls=RecordsInvalidOutput,
                **llm_kwargs,
            )
            s.attributes["repaired"] = repaired
            issues = record_issues(extraction, today, booked_pet)
            result = RecordsResult(
                extraction=extraction,
                evidence=to_evidence(extraction),
                issues=tuple(issues),
                outcome=RecordsOutcome.NEEDS_REVIEW if issues else RecordsOutcome.CLEAR,
            )

        s.output = {
            "extraction": result.extraction.model_dump(mode="json") if result.extraction else None,
            "issues": list(result.issues),
            "outcome": result.outcome,
        }
        return result
