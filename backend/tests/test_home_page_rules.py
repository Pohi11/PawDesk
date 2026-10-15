"""The booking rules the home page shows match the ones the backend uses (spec:
run-dashboard). The page reads frontend/content/booking-rules.json; this test compares that
file with the seeded facility's vaccine rules, the size class SQL, and the booking horizon."""

import json
import re
from pathlib import Path

import pytest

from app.enums import Service, Species
from app.intake import BOOKING_HORIZON_DAYS
from app.models.domain import SIZE_CLASS_SQL
from scripts.seed import RULES

spec = pytest.mark.spec
REQUIREMENT = "The home page explains the booking rules"
DATA = Path(__file__).resolve().parents[2] / "frontend" / "content" / "booking-rules.json"


@pytest.fixture(scope="module")
def page_rules() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


@spec("run-dashboard", REQUIREMENT)
def test_vaccine_lists_match_the_seeded_rules(page_rules):
    shown = {
        (Service(s["service"]), Species(species)): vaccines
        for s in page_rules["services"]
        for species, vaccines in s["vaccines"].items()
    }
    seeded = {key: [str(v) for v in vaccines] for key, vaccines in RULES.items()}
    assert shown == seeded


@spec("run-dashboard", REQUIREMENT)
def test_every_vaccine_shown_has_a_name(page_rules):
    used = {v for s in page_rules["services"] for vs in s["vaccines"].values() for v in vs}
    assert used <= page_rules["vaccine_names"].keys()


@spec("run-dashboard", REQUIREMENT)
def test_only_boarding_needs_a_kennel(page_rules):
    # The orchestrator searches for a kennel only for boarding (`_capacity`).
    assert {s["service"]: s["kennel"] for s in page_rules["services"]} == {
        "boarding": True,
        "daycare": False,
        "grooming": False,
    }


@spec("run-dashboard", REQUIREMENT)
def test_dog_weight_bands_match_the_size_class_sql(page_rules):
    thresholds = re.findall(r"WHEN weight_lb < (\d+) THEN '(\w+)'", SIZE_CLASS_SQL)
    expected = [(size, int(lb)) for lb, size in thresholds]
    expected.append(("xlarge", None))  # the ELSE branch
    shown = [(band["size"], band["under_lb"]) for band in page_rules["dog_sizes"]]
    assert shown == expected


@spec("run-dashboard", REQUIREMENT)
def test_booking_horizon_matches_intake(page_rules):
    assert page_rules["booking_horizon_days"] == BOOKING_HORIZON_DAYS
