"""Spec: certificate-evaluation, the committed benchmark set on disk."""

import json

import pytest

from scripts.generate_certificates import CERT_DIR, TRUTH_FILE, make_truth

spec = pytest.mark.spec


@spec("certificate-evaluation", "Certificates are generated with ground truth")
def test_committed_set_has_an_image_for_every_truth_entry():
    if not TRUTH_FILE.exists():
        pytest.fail("certificate set not generated: uv run python -m scripts.generate_certificates")
    truth = json.loads(TRUTH_FILE.read_text(encoding="utf-8"))
    certs = truth["certificates"]

    assert len(certs) >= 30
    for cert in certs:
        assert (CERT_DIR / cert["file"]).is_file(), cert["file"]
    assert certs == make_truth(seed=truth["seed"], n=len(certs))  # committed truth == generator
