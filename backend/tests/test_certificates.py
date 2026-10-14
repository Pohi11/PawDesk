"""Spec: certificate-evaluation, the synthetic certificate set (rendering not needed here)."""

from collections import Counter

import pytest

from scripts.generate_certificates import (
    CLINICS,
    LAYOUTS,
    VARIANTS,
    WATERMARK,
    make_truth,
    render_html,
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
