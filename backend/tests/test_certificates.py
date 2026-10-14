"""Spec: certificate-evaluation, the synthetic certificate set (rendering not needed here)."""

from collections import Counter
from datetime import timedelta

import pytest

from scripts.generate_certificates import (
    CLINICS,
    LAYOUTS,
    STAY_END,
    VARIANTS,
    WATERMARK,
    make_truth,
    make_truth_v2,
    reference_decision,
    render_html,
    verify_decision,
)

spec = pytest.mark.spec


@spec("certificate-evaluation", "Certificates are generated with ground truth")
def test_ground_truth_is_deterministic():
    assert make_truth(seed=7) == make_truth(seed=7)
    assert make_truth(seed=7) != make_truth(seed=8)


@spec("certificate-evaluation", "Certificates are generated with ground truth")
def test_truth_records_are_consistent():
    for cert in make_truth():
        assert cert["records"], cert["id"]
        for r in cert["records"]:
            if r["expires_on"] is not None:
                assert r["expires_on"] >= r["administered_on"], cert["id"]


@spec("certificate-evaluation", "The set covers hard cases")
def test_variant_and_layout_coverage():
    certs = make_truth()
    layouts = Counter(c["layout"] for c in certs)
    variants = Counter(c["variant"] for c in certs)

    assert len(certs) >= 30
    assert set(layouts) == set(LAYOUTS) and min(layouts.values()) >= 4
    assert set(variants) == set(VARIANTS) and min(variants.values()) >= 4
    missing = [c for c in certs if c["variant"] == "missing_expiry"]
    assert all(any(r["expires_on"] is None for r in c["records"]) for c in missing)


@spec("certificate-evaluation", "Certificates are visibly synthetic")
def test_every_certificate_is_marked_synthetic_and_fictional():
    for cert in make_truth():
        page = render_html(cert)
        assert "SYNTHETIC TEST DOCUMENT" in page
        assert WATERMARK in page
        assert cert["clinic"] in CLINICS


@spec("certificate-evaluation", "Certificates are generated with ground truth")
def test_fonts_are_embedded_not_fetched_from_disk():
    page = render_html(make_truth()[0])

    assert page.count("url(data:font/ttf;base64,") == 3
    assert "file://" not in page


# --- Benchmark v2 ---------------------------------------------------------------------


@spec("certificate-evaluation", "Certificates are generated with ground truth")
def test_v2_ground_truth_is_deterministic():
    assert make_truth_v2() == make_truth_v2()


@spec("certificate-evaluation", "The set covers hard cases")
def test_v2_keeps_layout_and_variant_coverage():
    certs = make_truth_v2()

    assert min(Counter(c["layout"] for c in certs).values()) >= 4
    assert min(Counter(c["variant"] for c in certs).values()) >= 4


@spec("certificate-evaluation", "Reference decisions are balanced")
def test_v2_decision_mix():
    certs = make_truth_v2()
    decisions = Counter(reference_decision(c) for c in certs)

    assert max(decisions["compliant"], decisions["not_compliant"]) <= 0.6 * len(certs)
    assert decisions["needs_review"] >= 4
    assert all(reference_decision(c) == c["decision"] for c in certs)


@spec("certificate-evaluation", "Reference decisions are balanced")
def test_v2_boundary_coverage():
    certs = make_truth_v2()
    required = {"dog": {"rabies", "dhpp", "bordetella"}, "cat": {"rabies", "fvrcp"}}

    def expiring_on(cert, day):
        return any(
            r["vaccine"] in required[cert["species"]] and r["expires_on"] == day.isoformat()
            for r in cert["records"]
        )

    on_checkout = [c for c in certs if c["decision"] == "compliant" and expiring_on(c, STAY_END)]
    day_before = [
        c
        for c in certs
        if c["decision"] == "not_compliant" and expiring_on(c, STAY_END - timedelta(days=1))
    ]
    assert len(on_checkout) >= 4
    assert len(day_before) >= 4


@spec("certificate-evaluation", "Reference decisions are balanced")
def test_generator_refuses_a_certificate_that_misses_its_target():
    cert = make_truth_v2()[0]

    wrong = "not_compliant" if cert["decision"] != "not_compliant" else "compliant"
    with pytest.raises(ValueError, match="compliance says"):
        verify_decision(cert, wrong)
