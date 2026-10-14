"""Spec: delivery-pipeline, the pipeline definition."""

import re

import pytest
import yaml

from scripts.secret_scan import REPO

spec = pytest.mark.spec
REQ = "Every change is checked automatically"
WORKFLOW = REPO / ".github" / "workflows" / "ci.yml"


@pytest.fixture(scope="module")
def workflow() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def commands(job: dict) -> str:
    return "\n".join(step.get("run", "") for step in job["steps"])


@spec("delivery-pipeline", REQ)
def test_runs_on_every_push_and_pull_request(workflow):
    # YAML 1.1 reads the bare key `on` as True.
    triggers = workflow.get("on", workflow.get(True))
    assert set(triggers) == {"push", "pull_request"}


@spec("delivery-pipeline", REQ)
def test_every_check_has_a_job(workflow):
    jobs = workflow["jobs"]

    assert set(jobs) == {"backend", "frontend", "e2e", "traceability", "secrets"}
    backend = commands(jobs["backend"])
    for check in ("ruff check", "alembic upgrade head", "alembic check", "pytest --junitxml"):
        assert check in backend
    assert jobs["backend"]["services"]["postgres"]["image"].startswith("postgres:18")
    frontend = commands(jobs["frontend"])
    for check in ("pnpm lint", "pnpm typecheck", "pnpm test", "pnpm build"):
        assert check in frontend
    assert "pnpm e2e" in commands(jobs["e2e"])
    assert "scripts.walkthrough --check" in commands(jobs["traceability"])
    assert set(jobs["traceability"]["needs"]) == {"backend", "frontend", "e2e"}
    assert any("gitleaks" in step.get("uses", "") for step in jobs["secrets"]["steps"])


@spec("delivery-pipeline", REQ)
def test_no_model_key_is_used(workflow):
    text = WORKFLOW.read_text(encoding="utf-8")

    assert re.findall(r"secrets\.(\w+)", text) == ["GITHUB_TOKEN"]  # the scanner's own token
    assert workflow["env"]["OPENROUTER_API_KEY"].endswith("placeholder-replay-only")
    assert "PAWDESK_E2E_RECORD" not in text  # CI only ever replays
