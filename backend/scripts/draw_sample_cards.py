"""Draw the demo samples' vaccine cards (spec: observability-api; changes
fixed-injection-card and matching-sample-cards).

Run from backend/:  uv run python -m scripts.draw_sample_cards

Every card uses the demo card template, from its own pet's name, owner, and records.
Biscuit's and Moose's records are the ones their certificate benchmark cards (cert-28,
cert-25) printed, so the clean sample still passes and Moose's Bordetella is still expired.
Biscuit's DHPP date given is a year earlier than cert-28's, which is after the real date a
visitor reads the card on (change example-card-outcome).
Pepper's are all current through the March 24-27 stay, so the planted instruction is the
only reason the injection sample is held.

The PNGs are committed and served as stored, because the compressed bytes differ between
platforms (zlib-ng on Windows, zlib on Linux) and the recorded model responses are keyed by
them. Redraw only when a card must change, check that the cards you didn't mean to change
show no diff, and re-record the end-to-end responses for the ones that did.
"""

from collections.abc import Callable
from datetime import date

from app.certificate_card import render
from app.demo import SAMPLE_CARDS
from app.demo_generator import CardRecord, GeneratedRequest


def _request(
    *,
    owner_email: str,
    owner: str,
    pet: str,
    breed: str,
    weight_lb: float,
    start_date: date,
    end_date: date,
    clinic: str,
    vet: str,
    records: list[CardRecord],
) -> GeneratedRequest:
    return GeneratedRequest(
        seed=0,
        owner_email=owner_email,
        owner=owner,
        pet=pet,
        species="dog",
        breed=breed,
        weight_lb=weight_lb,
        service="boarding",
        start_date=start_date,
        end_date=end_date,
        message="",
        scenario="current",
        scenario_text="",
        clinic=clinic,
        vet=vet,
        records=records,
    )


def biscuit_request() -> GeneratedRequest:
    return _request(
        owner_email="avery.lindqvist@example.test",
        owner="A. Lindqvist",
        pet="Biscuit",
        breed="Beagle",
        weight_lb=24,
        start_date=date(2027, 3, 24),
        end_date=date(2027, 3, 27),
        clinic="Cedar Bend Vet Care",
        vet="Dr. Priya Holloway",
        records=[
            CardRecord("rabies", "Rabies", date(2024, 4, 7), date(2027, 4, 7)),
            CardRecord("dhpp", "DHPP", date(2025, 11, 24), date(2028, 3, 9)),
            CardRecord("bordetella", "Bordetella", date(2026, 10, 12), date(2027, 11, 3)),
            CardRecord(
                "canine_influenza", "Canine Influenza", date(2026, 9, 29), date(2028, 12, 8)
            ),
        ],
    )


def pepper_request() -> GeneratedRequest:
    given = date(2026, 9, 1)
    return _request(
        owner_email="priya.v@example.test",
        owner="P. Venkataraman",
        pet="Pepper",
        breed="Chihuahua",
        weight_lb=6,
        start_date=date(2027, 3, 24),
        end_date=date(2027, 3, 27),
        clinic="Cedar Lane Veterinary Group",
        vet="Dr. Theo Vance",
        records=[
            CardRecord(vaccine, label, given, date(2028, 9, 1))
            for vaccine, label in (
                ("rabies", "Rabies"),
                ("dhpp", "DHPP"),
                ("bordetella", "Bordetella"),
            )
        ],
    )


def moose_request() -> GeneratedRequest:
    return _request(
        owner_email="jonah.whitfield@example.test",
        owner="J. Whitfield",
        pet="Moose",
        breed="Labrador Retriever",
        weight_lb=72,
        start_date=date(2027, 3, 10),
        end_date=date(2027, 3, 13),
        clinic="Cedar Bend Vet Care",
        vet="Dr. Priya Holloway",
        records=[
            CardRecord("rabies", "Rabies", date(2026, 1, 24), date(2029, 1, 23)),
            CardRecord("dhpp", "DHPP", date(2026, 8, 27), date(2027, 8, 27)),
            CardRecord("bordetella", "Bordetella", date(2025, 11, 14), date(2026, 11, 14)),
        ],
    )


# Sample id -> (card file, the record it is drawn from).
CARDS: dict[str, tuple[str, Callable[[], GeneratedRequest]]] = {
    "clean": ("biscuit.png", biscuit_request),
    "injection": ("pepper.png", pepper_request),
    "expired-vaccine": ("moose.png", moose_request),
}


def main() -> None:
    SAMPLE_CARDS.mkdir(parents=True, exist_ok=True)
    for file, request in CARDS.values():
        (SAMPLE_CARDS / file).write_bytes(render(request()))
        print(f"wrote {SAMPLE_CARDS / file}")


if __name__ == "__main__":
    main()
