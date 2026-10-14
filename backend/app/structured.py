"""Structured output from a model: strict schema in, Pydantic-validated object out.

Shared by every step that reads messy input (intake, records). One implementation of the
rules: a strict JSON schema derived from the same Pydantic model that validates, temperature
0, and exactly one repair attempt that shows the model its validation errors.
"""

import copy
from typing import Any

from pydantic import BaseModel, ValidationError

from app.llm import complete

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

REPAIR_INSTRUCTION = (
    "Your previous output failed validation:\n{errors}\n"
    "Return only the corrected JSON object, with every field."
)


class InvalidModelOutput(Exception):
    """The model's output failed validation, and so did the one repair attempt."""


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
    """The provider-side schema, derived from the same model that validates."""
    schema = model.model_json_schema()
    defs = schema.pop("$defs", {})
    schema.pop("description", None)  # the class docstring is for developers, not the model
    return _strictify(schema, defs)


def response_format_for(model: type[BaseModel], name: str) -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {"name": name, "strict": True, "schema": strict_json_schema(model)},
    }


def validation_errors(exc: ValidationError) -> str:
    lines = [f"- {'.'.join(map(str, e['loc'])) or 'output'}: {e['msg']}" for e in exc.errors()]
    return "\n".join(lines)[:1000]


async def extract[M: BaseModel](
    model: type[M],
    messages: list[dict[str, Any]],
    *,
    name: str,
    schema_name: str,
    error_cls: type[InvalidModelOutput] = InvalidModelOutput,
    **llm_kwargs: Any,
) -> tuple[M, bool]:
    """Call the model, validate, and repair once. Returns (instance, repaired).

    Model calls are traced as `<name>.extract` and, if needed, `<name>.repair`.
    """
    common = {
        "response_format": response_format_for(model, schema_name),
        "temperature": 0,
        **llm_kwargs,
    }
    first = await complete(messages, name=f"{name}.extract", **common)
    try:
        return model.model_validate_json(first.text), False
    except ValidationError as exc:
        errors = validation_errors(exc)

    repair_messages = [
        *messages,
        {"role": "assistant", "content": first.text},
        {"role": "user", "content": REPAIR_INSTRUCTION.format(errors=errors)},
    ]
    second = await complete(repair_messages, name=f"{name}.repair", **common)
    try:
        return model.model_validate_json(second.text), True
    except ValidationError as exc:
        raise error_cls(f"{name} output invalid after repair: {validation_errors(exc)}") from exc
