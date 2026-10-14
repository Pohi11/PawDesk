"""Spec: certificate-evaluation, the committed benchmark sets on disk (every version)."""

import json

import pytest

from scripts.generate_certificates import BENCHMARK_DIRS, SEEDS, make_benchmark

spec = pytest.mark.spec


@spec("certificate-evaluation", "Certificates are generated with ground truth")
@spec("certificate-evaluation", "Benchmark versions are kept side by side")
@pytest.mark.parametrize("version", sorted(BENCHMARK_DIRS))
def test_committed_set_matches_its_generator(version):
    base = BENCHMARK_DIRS[version]
    truth_file = base / "truth.json"
    if not truth_file.exists():
        pytest.fail(
            f"{version} not generated: uv run python -m scripts.generate_certificates {version}"
        )
    truth = json.loads(truth_file.read_text(encoding="utf-8"))
    certs = truth["certificates"]

    assert truth.get("version", "v1") == version
    assert truth["seed"] == SEEDS[version]
    assert len(certs) >= 30
    for cert in certs:
        assert (base / cert["file"]).is_file(), f"{version} {cert['file']}"
    assert certs == make_benchmark(version)  # committed truth == generator, v1 untouched
