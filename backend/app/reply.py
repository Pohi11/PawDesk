"""The reply: drafted by a model from structured facts, checked by code before it can be
sent (spec: booking-reply; decision record 0011).

The model writes the words. Code decides the situation (what the reply may say), which
options it may offer (verified ones only), and whether the draft over-promises.
"""

import re
from dataclasses import asdict, dataclass, field
from datetime import date
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.enums import SpanKind
from app.prompts.reply import PROMPT_VERSION, build_messages
from app.structured import InvalidModelOutput, extract
from app.tracing import span


class Situation(StrEnum):
    CONFIRMED = "confirmed"  # passed every check without resolving
    ALTERNATIVES = "alternatives"  # resolver proposed at least one verified option
    UNDER_REVIEW = "under_review"  # nothing to confirm or offer: a person will follow up


Subject = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Body = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1500)]


class ReplyDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: Subject
    body: Body


class ReplyInvalidOutput(InvalidModelOutput):
    """The draft failed validation, and so did the one repair attempt."""


@dataclass(frozen=True)
class ReplyFacts:
    owner_first_name: str
    pet_name: str
    facility: str
    service: str | None
    start_date: date | None
    end_date: date | None
    situation: Situation
    options: list[dict[str, Any]] = field(default_factory=list)  # verified only
    vaccines_needed: list[str] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        facts = asdict(self)
        for key in ("start_date", "end_date"):
            facts[key] = facts[key].isoformat() if facts[key] else None
        facts["situation"] = str(self.situation)
        return facts

    def allowed_ranges(self) -> list[tuple[date, date]]:
        """Every date a reply may mention: the requested stay and each verified window."""
        ranges = []
        if self.start_date and self.end_date:
            ranges.append((self.start_date, self.end_date))
        for option in self.options:
            if option["kind"] == "alternative_dates":
                ranges.append(
                    (
                        date.fromisoformat(option["start_date"]),
                        date.fromisoformat(option["end_date"]),
                    )
                )
        return ranges


def situation_for(route: dict, resolution: dict | None) -> Situation:
    if route["target"] == "drafting":
        return Situation.CONFIRMED
    proposal = (resolution or {}).get("proposal") or {}
    if any(option["verified"] for option in proposal.get("options", [])):
        return Situation.ALTERNATIVES
    return Situation.UNDER_REVIEW


def reply_facts(
    *,
    owner_name: str,
    pet_name: str | None,
    facility: str,
    intake: dict,
    route: dict,
    resolution: dict | None,
) -> ReplyFacts:
    """Names come from the rows on file, never from the message as written."""
    situation = situation_for(route, resolution)
    intent = intake["intent"] or {}
    options = []
    if situation == Situation.ALTERNATIVES:
        options = [
            {k: v for k, v in option.items() if k not in ("verified", "remaining_problems")}
            for option in resolution["proposal"]["options"]
            if option["verified"]
        ]
    return ReplyFacts(
        owner_first_name=owner_name.split()[0],
        pet_name=pet_name or "your pet",
        facility=facility,
        service=intent.get("service"),
        start_date=_date(intent.get("start_date")),
        end_date=_date(intent.get("end_date")),
        situation=situation,
        options=options,
        vaccines_needed=sorted(
            {
                v
                for option in options
                if option["kind"] == "vaccine_update"
                for v in option["vaccines"]
            }
        ),
    )


def _date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


# --- The promise check (design D3) ------------------------------------------------------

MONTHS = {
    name: n
    for n, names in enumerate(
        [
            ("jan", "january"),
            ("feb", "february"),
            ("mar", "march"),
            ("apr", "april"),
            ("may",),
            ("jun", "june"),
            ("jul", "july"),
            ("aug", "august"),
            ("sep", "sept", "september"),
            ("oct", "october"),
            ("nov", "november"),
            ("dec", "december"),
        ],
        start=1,
    )
    for name in names
}
_MONTH = "(" + "|".join(sorted(MONTHS, key=len, reverse=True)) + r")\.?"
_DAY = r"(\d{1,2})(?:st|nd|rd|th)?"
_RANGE_END = r"(?:\s*(?:-|–|—|to|through|thru|until)\s*" + _DAY + r"\b(?!\s*/))?"
DATE_PATTERNS = [
    # "March 10", "Mar 10th", "March 10-13", "March 10 to 13"
    ("month_day", re.compile(rf"\b{_MONTH}\s+{_DAY}\b{_RANGE_END}", re.IGNORECASE)),
    # "10 March", "10th of March"
    ("day_month", re.compile(rf"\b{_DAY}\s+(?:of\s+)?{_MONTH}\b", re.IGNORECASE)),
    # "2027-03-10"
    ("iso", re.compile(r"\b\d{4}-(\d{2})-(\d{2})\b")),
    # "3/10" or "3/10/2027" (month first)
    ("numeric", re.compile(r"\b(\d{1,2})/(\d{1,2})(?:/\d{2,4})?\b")),
]
COMMITMENT = re.compile(r"\b(booked|confirmed|reserved|approved)\b", re.IGNORECASE)
MONEY = re.compile(r"(\$\s?\d|\bUSD\s?\d|\b\d+(?:[.,]\d+)?\s?(?:dollars|usd)\b)", re.IGNORECASE)


def mentioned_dates(body: str) -> list[tuple[str, int, int]]:
    """(text as written, month, day) for every date-like mention in the body."""
    found = []
    for kind, pattern in DATE_PATTERNS:
        for m in pattern.finditer(body):
            if kind == "month_day":
                month, days = MONTHS[m[1].lower()], [m[2], m[3]]
            elif kind == "day_month":
                month, days = MONTHS[m[2].lower()], [m[1]]
            else:
                month, days = int(m[1]), [m[2]]
            for day in filter(None, days):
                found.append((m[0], month, int(day)))
    return [(text, month, day) for text, month, day in found if 1 <= month <= 12 and 1 <= day <= 31]


def promise_issues(body: str, facts: ReplyFacts) -> list[str]:
    """Everything in the draft that commits the facility beyond what the checks confirmed."""
    allowed = {
        (d.month, d.day)
        for start, end in facts.allowed_ranges()
        for d in (date.fromordinal(n) for n in range(start.toordinal(), end.toordinal() + 1))
    }
    issues = []
    for text, month, day in mentioned_dates(body):
        if (month, day) not in allowed:
            issue = f"unconfirmed date: {text!r}"
            if issue not in issues:
                issues.append(issue)
    if facts.situation != Situation.CONFIRMED:
        issues += [
            f"commitment word in a reply that confirms nothing: {w!r}"
            for w in dict.fromkeys(m[1].lower() for m in COMMITMENT.finditer(body))
        ]
    issues += [f"mentions a price: {m[0]!r}" for m in MONEY.finditer(body)]
    return issues


# --- Drafting ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReplyResult:
    facts: ReplyFacts
    draft: ReplyDraft
    promise_issues: list[str]


async def draft_reply(facts: ReplyFacts, **llm_kwargs: Any) -> ReplyResult:
    async with span("reply", SpanKind.CODE, input={"situation": str(facts.situation)}) as s:
        s.attributes["prompt_version"] = PROMPT_VERSION
        draft, repaired = await extract(
            ReplyDraft,
            build_messages(facts.to_json()),
            name="reply",
            schema_name="reply_draft",
            error_cls=ReplyInvalidOutput,
            **llm_kwargs,
        )
        issues = promise_issues(draft.body, facts)
        s.output = {"draft": draft.model_dump(), "promise_issues": issues, "repaired": repaired}
        return ReplyResult(facts, draft, issues)
