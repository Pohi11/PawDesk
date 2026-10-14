"""Spec: build-walkthrough, the generator against a small synthetic repository."""

import json
from pathlib import Path
from textwrap import dedent

import pytest

from scripts.walkthrough import Sources, build, humanize, main, problems

spec = pytest.mark.spec
MARKER = "PRIVATE-MARKER-7f3a"

SPEC_A = """\
    # alpha Specification

    ## Purpose

    Alpha things.

    ## Requirements

    ### Requirement: Alpha works
    The system SHALL alpha.

    #### Scenario: Plain alpha
    - **WHEN** alpha happens
    - **THEN** it works

    ### Requirement: Alpha fails loudly
    The system SHALL fail loudly.

    #### Scenario: Loud
    - **WHEN** it breaks
    - **THEN** it says so

    ### Requirement: Alpha is documented
    The system SHALL be documented.

    #### Scenario: Docs
    - **WHEN** read
    - **THEN** understood
"""


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text), encoding="utf-8")


def change(repo: Path, folder: str, why: str, decision: str | None = None) -> None:
    base = repo / "openspec" / "changes" / "archive" / folder
    link = f"See [0008](../../../../docs/decisions/{decision}.md)." if decision else ""
    write(base / "proposal.md", f"# Proposal\n\n## Why\n\n{why}\n\n## What Changes\n\n- a thing\n")
    write(base / "design.md", f"# Design\n\n{link}\n")
    write(
        base / "tasks.md",
        "# Tasks\n\n## 1. Build\n\n- [x] 1.1 Do it. Verify it.\n- [ ] 1.2 Later.\n",
    )
    write(
        base / "specs" / "alpha" / "spec.md",
        "# Spec Delta\n\n## ADDED Requirements\n\n### Requirement: Alpha works\nx\n\n"
        "#### Scenario: s\n- **WHEN** a\n- **THEN** b\n",
    )


def junit_backend(path: Path, cases: list[tuple[str, str, str | None]]) -> None:
    rows = []
    for name, outcome, link in cases:
        props = f'<properties><property name="spec" value="{link}"/></properties>' if link else ""
        inner = {"passed": "", "failed": "<failure message='x'/>", "skipped": "<skipped/>"}[outcome]
        rows.append(
            f'<testcase classname="tests.test_a" name="{name}" time="0.5">{props}{inner}</testcase>'
        )
    write(
        path,
        '<testsuites><testsuite name="pytest" timestamp="2026-10-14T10:00:00">'
        + "".join(rows)
        + "</testsuite></testsuites>",
    )


def junit_frontend(path: Path, names: list[str]) -> None:
    rows = "".join(f'<testcase classname="lib/a.test.ts" name="{n}" time="0.01"/>' for n in names)
    write(
        path,
        f'<testsuites><testsuite name="lib/a.test.ts" timestamp="2026-10-14T10:01:00">{rows}</testsuite></testsuites>',
    )


@pytest.fixture
def repo(tmp_path) -> Path:
    write(tmp_path / "openspec" / "specs" / "alpha" / "spec.md", SPEC_A)
    change(tmp_path, "2026-10-14-phase-02-second", "Second because.", "0008-hybrid")
    change(tmp_path, "2026-10-13-phase-01-first", "First because.")
    change(tmp_path, "2026-10-15-extra-change", "Third because.")
    write(
        tmp_path / "docs" / "decisions" / "0008-hybrid.md",
        "# 0008 — Hybrid beats agentic\n\n- **Date:** 2026-10-14\n- **Status:** Accepted\n\n## Context\n\nWhy.\n",
    )
    # Private files the generator must never read.
    write(tmp_path / "docs" / "private" / "notes.md", f"secret {MARKER}\n")
    write(tmp_path / "CLAUDE.md", f"agreement {MARKER}\n")
    write(tmp_path / "PLAN.md", f"plan {MARKER}\n")
    junit_backend(
        tmp_path / "backend.xml",
        [
            ("test_works", "passed", "alpha: Alpha works"),
            ("test_fails", "failed", "alpha: Alpha fails loudly"),
            ("test_infra", "passed", None),
        ],
    )
    junit_frontend(
        tmp_path / "frontend.xml", ["[spec alpha: Alpha works] renders alpha", "untagged"]
    )
    return tmp_path


def sources(repo: Path) -> Sources:
    return Sources.of(repo, repo / "backend.xml", repo / "frontend.xml")


def requirement(data, name):
    return next(r for c in data["specs"] for r in c["requirements"] if r["name"] == name)


# --- The walkthrough is generated from public sources only ------------------------------


@spec("build-walkthrough", "The walkthrough is generated from public sources only")
def test_every_archived_change_appears_in_date_order(repo):
    data = build(sources(repo))

    assert [c["date"] for c in data["changes"]] == ["2026-10-13", "2026-10-14", "2026-10-15"]
    first = data["changes"][0]
    assert (first["title"], first["why"]) == ("Phase 1 · First", "First because.")
    assert first["tasks"] == [
        {
            "title": "1. Build",
            "items": [
                {"id": "1.1", "done": True, "text": "Do it. Verify it."},
                {"id": "1.2", "done": False, "text": "Later."},
            ],
        }
    ]
    assert first["requirements"] == [
        {"capability": "alpha", "kind": "added", "name": "Alpha works"}
    ]
    assert data["totals"]["changes"] == 3
    assert data["reports"] == {"backend": "2026-10-14T10:00:00", "frontend": "2026-10-14T10:01:00"}


@spec("build-walkthrough", "The walkthrough is generated from public sources only")
def test_private_files_are_never_read(repo, tmp_path):
    out = tmp_path / "out.json"
    main(
        [
            "--repo",
            str(repo),
            "--backend-junit",
            str(repo / "backend.xml"),
            "--frontend-junit",
            str(repo / "frontend.xml"),
            "--out",
            str(out),
        ]
    )

    assert MARKER not in out.read_text(encoding="utf-8")
    assert json.loads(out.read_text(encoding="utf-8"))["generated_at"]


# --- Requirements link to their tests and latest results --------------------------------


@spec("build-walkthrough", "Requirements link to their tests and latest results")
def test_verified_requirement_lists_backend_and_frontend_tests(repo):
    req = requirement(build(sources(repo)), "Alpha works")

    assert req["status"] == "verified"
    assert [(t["suite"], t["id"], t["status"]) for t in req["tests"]] == [
        ("backend", "tests.test_a::test_works", "passed"),
        ("frontend", "lib/a.test.ts::renders alpha", "passed"),
    ]
    assert req["scenarios"] == [
        {"name": "Plain alpha", "steps": ["**WHEN** alpha happens", "**THEN** it works"]}
    ]


@spec("build-walkthrough", "Requirements link to their tests and latest results")
def test_failing_and_untested_requirements(repo):
    data = build(sources(repo))

    assert requirement(data, "Alpha fails loudly")["status"] == "failing"
    assert requirement(data, "Alpha is documented")["status"] == "untested"
    assert data["totals"]["verified"] == 1


# --- Changes link to the decisions they relied on ---------------------------------------


@spec("build-walkthrough", "Changes link to the decisions they relied on")
def test_decision_linked_from_a_change(repo):
    data = build(sources(repo))

    second = next(c for c in data["changes"] if c["slug"] == "phase-02-second")
    assert second["decisions"] == ["0008"]
    [decision] = data["decisions"]
    assert (decision["number"], decision["title"], decision["date"], decision["status"]) == (
        "0008",
        "Hybrid beats agentic",
        "2026-10-14",
        "Accepted",
    )
    assert "## Context" in decision["markdown"]


# --- The coverage check fails on gaps ---------------------------------------------------


def run_check(repo, capsys) -> tuple[int, str]:
    code = main(
        [
            "--repo",
            str(repo),
            "--backend-junit",
            str(repo / "backend.xml"),
            "--frontend-junit",
            str(repo / "frontend.xml"),
            "--check",
        ]
    )
    return code, capsys.readouterr().out


@spec("build-walkthrough", "The coverage check fails on gaps")
def test_gaps_fail_the_check(repo, capsys):
    junit_frontend(repo / "frontend.xml", ["[spec alpha: No such requirement] ghost"])

    code, out = run_check(repo, capsys)

    assert code == 1
    assert "failing: alpha: Alpha fails loudly" in out
    assert "untested: alpha: Alpha is documented" in out
    assert "unknown requirement 'alpha: No such requirement'" in out


@spec("build-walkthrough", "The coverage check fails on gaps")
def test_complete_coverage_passes(repo, capsys):
    junit_backend(
        repo / "backend.xml",
        [
            ("test_works", "passed", "alpha: Alpha works"),
            ("test_fails", "passed", "alpha: Alpha fails loudly"),
            ("test_docs", "passed", "alpha: Alpha is documented"),
        ],
    )

    code, out = run_check(repo, capsys)

    assert code == 0
    assert "3/3 requirements verified" in out


@spec("build-walkthrough", "The coverage check fails on gaps")
def test_requirements_of_an_unarchived_change_must_be_covered_too(repo, capsys):
    write(
        repo / "openspec" / "changes" / "phase-03-next" / "specs" / "beta" / "spec.md",
        "# Spec Delta\n\n## ADDED Requirements\n\n### Requirement: Beta works\nx\n",
    )
    junit_backend(
        repo / "backend.xml",
        [
            ("test_works", "passed", "alpha: Alpha works"),
            ("test_fails", "passed", "alpha: Alpha fails loudly"),
            ("test_docs", "passed", "alpha: Alpha is documented"),
        ],
    )

    code, out = run_check(repo, capsys)

    assert code == 1
    assert "untested (pending change): beta: Beta works" in out
    assert problems(sources(repo), build(sources(repo))) == [
        "untested (pending change): beta: Beta works"
    ]


def test_titles_read_naturally():
    assert humanize("phase-03-llm-tracing") == "Phase 3 · LLM tracing"
    assert humanize("phase-09b-build-walkthrough") == "Phase 9b · Build walkthrough"
    assert humanize("certificate-benchmark-v2") == "Certificate benchmark v2"


@spec("build-walkthrough", "Requirements link to their tests and latest results")
def test_end_to_end_tests_count(repo):
    junit_backend(repo / "backend.xml", [])
    junit_frontend(repo / "frontend.xml", [])
    junit_frontend(repo / "e2e.xml", ["[spec alpha: Alpha is documented] demo runs"])

    data = build(Sources.of(repo, repo / "backend.xml", repo / "frontend.xml", repo / "e2e.xml"))

    req = requirement(data, "Alpha is documented")
    assert req["status"] == "verified"
    assert [(t["suite"], t["id"]) for t in req["tests"]] == [("e2e", "lib/a.test.ts::demo runs")]
    assert data["totals"]["tests"] == {"backend": 0, "frontend": 0, "e2e": 1}
