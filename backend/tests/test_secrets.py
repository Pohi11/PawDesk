"""Spec: delivery-pipeline, secrets never enter the repository."""

import subprocess

import pytest

from scripts.secret_scan import REPO, find_secrets

spec = pytest.mark.spec
REQ = "Secrets never enter the repository"
FAKE = "sk-or-v1-" + "0123456789abcdef" * 4  # key-shaped, not a real key


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@spec("delivery-pipeline", REQ)
def test_key_shaped_value_in_a_tracked_file_is_found(tmp_path):
    git(tmp_path, "init", "-q")
    (tmp_path / "config.py").write_text(f'KEY = "{FAKE}"\n', encoding="utf-8")
    (tmp_path / "untracked.txt").write_text(FAKE, encoding="utf-8")
    git(tmp_path, "add", "config.py")

    findings = find_secrets(tmp_path)

    assert len(findings) == 1
    assert findings[0].startswith("config.py:1: sk-or-v1-012")
    assert FAKE not in findings[0]  # the report never repeats the value


@spec("delivery-pipeline", REQ)
def test_the_repository_is_clean():
    assert find_secrets(REPO) == []


@spec("delivery-pipeline", REQ)
def test_example_environment_holds_placeholders_only():
    example = (REPO / ".env.example").read_text(encoding="utf-8")

    assert "OPENROUTER_API_KEY=sk-or-v1-replace-me" in example
