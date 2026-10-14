"""Closed sets of values shared by the models, the database CHECK constraints, and later the
LLM output schemas. Stored as their lowercase string values (see design D3)."""

from enum import StrEnum


class Species(StrEnum):
    DOG = "dog"
    CAT = "cat"


class Service(StrEnum):
    BOARDING = "boarding"
    DAYCARE = "daycare"
    GROOMING = "grooming"


class SizeClass(StrEnum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    XLARGE = "xlarge"
    CAT = "cat"


class Vaccine(StrEnum):
    RABIES = "rabies"
    DHPP = "dhpp"
    BORDETELLA = "bordetella"
    CANINE_INFLUENZA = "canine_influenza"
    LEPTOSPIROSIS = "leptospirosis"
    FVRCP = "fvrcp"
    FELV = "felv"


class ApprovalAction(StrEnum):
    APPROVE = "approve"
    EDIT_AND_APPROVE = "edit_and_approve"
    REJECT = "reject"


class SpanKind(StrEnum):
    LLM = "llm"
    TOOL = "tool"
    CODE = "code"
    HUMAN = "human"


class SpanStatus(StrEnum):
    RUNNING = "running"
    OK = "ok"
    ERROR = "error"


class Step(StrEnum):
    """Steps whose results the orchestrator saves (spec: booking-orchestration)."""

    INTAKE = "intake"
    RECORDS = "records"
    CHECKS = "checks"
    ROUTE = "route"
    RESOLUTION = "resolution"
    REPLY = "reply"
