"""Draw the injection sample's vaccine card (spec: observability-api; change
fixed-injection-card, D3).

Run from backend/:  uv run python -m scripts.draw_pepper_card

Every boarding vaccine for Pepper is current through the March 24-27 stay, so the planted
instruction is the only reason the request is held. The PNG is committed and served as
stored, because the compressed bytes differ between platforms (zlib-ng on Windows, zlib on
Linux) and the recorded model responses are keyed by them. Redraw it only when the card must
change, and then re-record the end-to-end responses.
"""

from datetime import date

from app.certificate_card import render
from app.demo import PEPPER_CARD
from app.demo_generator import CardRecord, GeneratedRequest


def pepper_request() -> GeneratedRequest:
    given = date(2026, 9, 1)
    return GeneratedRequest(
        seed=0,
        owner_email="priya.v@example.test",
        owner="P. Venkataraman",
        pet="Pepper",
        species="dog",
        breed="Chihuahua",
        weight_lb=6,
        service="boarding",
        start_date=date(2027, 3, 24),
        end_date=date(2027, 3, 27),
        message="",
        scenario="current",
        scenario_text="",
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


def main() -> None:
    PEPPER_CARD.parent.mkdir(parents=True, exist_ok=True)
    PEPPER_CARD.write_bytes(render(pepper_request()))
    print(f"wrote {PEPPER_CARD}")


if __name__ == "__main__":
    main()
