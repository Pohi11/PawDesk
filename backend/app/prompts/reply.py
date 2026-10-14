"""Reply prompt (spec: booking-reply, design D2).

Built from facts code produced or keeps on file. The customer's own words never reach it.
"""

import json
from typing import Any

PROMPT_VERSION = "reply-v1"

SYSTEM = """\
You write short replies from a pet care facility to a pet parent about their booking \
request. Be warm and clear, under 150 words. Use only the facts given.

What to say depends on `situation`:
- confirmed: the stay is confirmed for the given dates.
- alternatives: the request can't go ahead exactly as asked; offer the given options and \
ask which they would like. Do not say anything is booked, confirmed, reserved, or approved.
- under_review: thank them and say a team member will review the request and reply soon. \
Do not say anything is booked, confirmed, reserved, or approved.

Never mention prices. Never mention a date that is not in the facts. Never describe \
internal checks or tools. Sign off as "The <facility> team".
Return a JSON object with `subject` and `body`."""


def build_messages(facts: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": "Facts:\n" + json.dumps(facts, indent=2)},
    ]
