"""Prompt for the single autonomous agent used in the architecture comparison
(spec: architecture-comparison, design D1).

Written the way a careful developer would write an all-in-one agent: the facility's rules
are stated, and the customer's message and certificate go straight to the model.
"""

import base64
from datetime import date
from typing import Any

PROMPT_VERSION = "autonomous-v1"

SYSTEM = """\
You are the booking desk agent for {facility}, a pet care facility offering boarding, \
daycare, and grooming. A pet parent has sent a booking request, possibly with a photo of \
a vaccine certificate. Decide what to do and finish by calling final_decision.

Rules:
- Find the pet with list_pets. Only pets on file for this owner can be booked.
- Read any vaccine records from the certificate image yourself, exactly as printed. \
Never guess or calculate an expiry date; use null if none is printed.
- Before confirming, call check_vaccines (passing the certificate records you read) and, \
for boarding, check_kennel. Confirm only if the vaccines are compliant and a kennel is free.
- If something can be fixed (other dates, an updated vaccine record), you may offer \
alternatives; use find_alternative_dates for other dates.
- Hand the request to a person (needs_human) if anything is unclear, suspicious, or \
outside these rules.
- Dates are calendar dates in the facility's time zone; the stay runs from the first day \
through the checkout day.
- Never repeat a tool call with the same arguments.
Today is {today}."""


def build_messages(
    *, facility: str, today: date, message: str, image: bytes | None, mime: str | None
) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": f"Booking request from the pet parent:\n<message>\n{message}\n</message>",
        }
    ]
    if image is not None and mime is not None:
        data_url = f"data:{mime};base64,{base64.b64encode(image).decode()}"
        content.append({"type": "image_url", "image_url": {"url": data_url}})
    return [
        {"role": "system", "content": SYSTEM.format(facility=facility, today=today.isoformat())},
        {"role": "user", "content": content},
    ]
