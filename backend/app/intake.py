"""Booking intake: untrusted pet-parent message -> validated intent + issues.

Spec: booking-intake. The model only *describes* the request; code decides identity
(pet matching), timing (date checks), and whether a person must look (issues).
"""

import copy
from datetime import date
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.enums import Service

Ambiguity = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class BookingIntent(BaseModel):
    """What the model must return. `extra="forbid"`: any unexpected field (say, an injected
    `"approved": true`) fails validation instead of being silently dropped."""

    model_config = ConfigDict(extra="forbid")

    pet_name: str | None = Field(description="The pet's name as written, or null if not given.")
    service: Service | None = Field(description="boarding, daycare, or grooming; null if unclear.")
    start_date: date | None = Field(description="First day on site, YYYY-MM-DD, or null.")
    end_date: date | None = Field(
        description="Last day on site (checkout day), YYYY-MM-DD, or null."
    )
    special_notes: str = Field(
        max_length=500, description="Care notes from the customer (diet, meds, behavior)."
    )
    confidence: float = Field(ge=0, le=1, description="How sure you are, from 0 to 1.")
    ambiguities: list[Ambiguity] = Field(
        max_length=10, description="Anything unclear or conflicting; empty if none."
    )


# Keys some providers' strict modes reject. Pydantic still enforces the real constraints.
_DROP_KEYS = {
    "title",
    "default",
    "format",
    "minimum",
    "maximum",
    "maxLength",
    "minLength",
    "maxItems",
    "minItems",
}


def _strictify(node: Any, defs: dict[str, Any]) -> Any:
    if isinstance(node, list):
        return [_strictify(item, defs) for item in node]
    if not isinstance(node, dict):
        return node
    if "$ref" in node:  # inline $defs: simplest form for every provider
        return _strictify(copy.deepcopy(defs[node["$ref"].rsplit("/", 1)[-1]]), defs)
    out = {k: _strictify(v, defs) for k, v in node.items() if k not in _DROP_KEYS}
    if out.get("type") == "object" and "properties" in out:
        out["required"] = list(out["properties"])  # strict mode: every field required
        out["additionalProperties"] = False
    return out


def strict_json_schema(model: type[BaseModel]) -> dict[str, Any]:
    """The provider-side schema, derived from the same model that validates (design D1)."""
    schema = model.model_json_schema()
    defs = schema.pop("$defs", {})
    schema.pop("description", None)  # the class docstring is for developers, not the model
    return _strictify(schema, defs)


def response_format() -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "booking_intent",
            "strict": True,
            "schema": strict_json_schema(BookingIntent),
        },
    }
