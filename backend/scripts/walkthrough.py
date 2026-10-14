"""Generate the build walkthrough from the repository's public sources, and check spec
coverage (spec: build-walkthrough; decision record 0014).

Run from backend/ after the test suites have written their JUnit reports:
    uv run pytest --junitxml=test-results/junit.xml
    (cd ../frontend && pnpm test)
    uv run python -m scripts.walkthrough            # writes frontend/content/walkthrough.json
    uv run python -m scripts.walkthrough --check    # exits 1 on any coverage gap

Only the sources listed in `Sources` are read. The working agreement, the build plan, and
docs/private/ are never opened.
"""

import argparse
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
FRONTEND_TAG = re.compile(r"^\[spec ([a-z0-9-]+): ([^\]]+)\] ")
DECISION_LINK = re.compile(r"decisions/(\d{4})-")
REQUIREMENT = re.compile(r"^### Requirement: (.+)$", re.MULTILINE)


@dataclass(frozen=True)
class Sources:
    archive: Path
    active: Path
    specs: Path
    decisions: Path
    backend_junit: Path
    frontend_junit: Path

    @classmethod
    def of(cls, repo: Path, backend_junit: Path, frontend_junit: Path) -> "Sources":
        return cls(
            archive=repo / "openspec" / "changes" / "archive",
            active=repo / "openspec" / "changes",
            specs=repo / "openspec" / "specs",
            decisions=repo / "docs" / "decisions",
            backend_junit=backend_junit,
            frontend_junit=frontend_junit,
        )


# --- Markdown helpers -------------------------------------------------------------------


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def section(markdown: str, heading: str) -> str:
    """The text under `## heading`, up to the next heading of the same or higher level."""
    match = re.search(
        rf"^## {re.escape(heading)}\s*$(.*?)(?=^## |\Z)", markdown, re.MULTILINE | re.DOTALL
    )
    return match.group(1).strip() if match else ""


def requirements_of(markdown: str) -> list[dict[str, Any]]:
    """Each `### Requirement:` with its text and its `#### Scenario:` blocks."""
    result = []
    blocks = re.split(r"^(?=### Requirement: )", markdown, flags=re.MULTILINE)
    for block in blocks:
        head = REQUIREMENT.match(block)
        if not head:
            continue
        body = re.split(r"^## ", block[head.end() :], maxsplit=1, flags=re.MULTILINE)[0]
        parts = re.split(r"^#### Scenario: (.+)$", body, flags=re.MULTILINE)
        scenarios = [
            {"name": parts[i].strip(), "steps": _steps(parts[i + 1])}
            for i in range(1, len(parts) - 1, 2)
        ]
        result.append(
            {"name": head.group(1).strip(), "text": parts[0].strip(), "scenarios": scenarios}
        )
    return result


def _steps(text: str) -> list[str]:
    return [line.strip()[2:] for line in text.splitlines() if line.strip().startswith("- ")]


def delta_requirements(markdown: str) -> dict[str, list[str]]:
    """Requirement names in a spec delta, grouped by ADDED / MODIFIED / REMOVED / RENAMED."""
    grouped: dict[str, list[str]] = {}
    for match in re.finditer(
        r"^## (ADDED|MODIFIED|REMOVED|RENAMED) Requirements\s*$", markdown, re.MULTILINE
    ):
        body = section(markdown[match.start() :], f"{match.group(1)} Requirements")
        grouped[match.group(1).lower()] = REQUIREMENT.findall(body)
    return grouped


ACRONYMS = {"llm": "LLM", "api": "API", "sse": "SSE"}


def _words(text: str) -> str:
    words = text.split("-")
    words = [ACRONYMS.get(w, w) for w in words]
    first = words[0] if words[0].isupper() else words[0].capitalize()
    return " ".join([first, *words[1:]])


def humanize(slug: str) -> str:
    phase = re.match(r"phase-(\d+)([a-z]?)-(.*)", slug)
    if phase:
        number, suffix, rest = phase.groups()
        return f"Phase {int(number)}{suffix} · {_words(rest)}"
    return _words(slug)


def archived_at(folder: Path) -> str | None:
    """When the change was archived: the commit that first added files at this path. Several
    changes can be archived on one day, and only the commit order says which came first."""
    try:
        out = subprocess.run(
            [
                "git",
                "-C",
                str(folder),
                "log",
                "--no-renames",
                "--diff-filter=A",
                "--format=%cI",
                "--",
                ".",
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        ).stdout.split()
    except (OSError, subprocess.SubprocessError):
        return None
    return min(out) if out else None


# --- Sources ----------------------------------------------------------------------------


def changes(src: Sources) -> list[dict[str, Any]]:
    result = []
    for folder in sorted(p for p in src.archive.iterdir() if p.is_dir()):
        date, slug = folder.name[:10], folder.name[11:]
        proposal, design, tasks = (
            _read(folder / f) for f in ("proposal.md", "design.md", "tasks.md")
        )
        deltas = []
        for spec in sorted((folder / "specs").glob("*/spec.md")):
            for kind, names in delta_requirements(_read(spec)).items():
                deltas += [{"capability": spec.parent.name, "kind": kind, "name": n} for n in names]
        result.append(
            {
                "id": folder.name,
                "slug": slug,
                "title": humanize(slug),
                "date": date,
                "archived_at": archived_at(folder),
                "why": section(proposal, "Why"),
                "what_changes": section(proposal, "What Changes"),
                "tasks": _tasks(tasks),
                "requirements": deltas,
                "decisions": sorted(set(DECISION_LINK.findall(proposal + design + tasks))),
            }
        )
    # Commit order where git knows it; otherwise the date in the folder name.
    return sorted(result, key=lambda c: (c["archived_at"] or f"{c['date']}T99", c["id"]))


def _tasks(markdown: str) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for line in markdown.splitlines():
        heading = re.match(r"^## (.+)$", line)
        item = re.match(r"^- \[([ xX])\] (\S+) (.*)$", line)
        if heading:
            groups.append({"title": heading.group(1).strip(), "items": []})
        elif item and groups:
            groups[-1]["items"].append(
                {"id": item.group(2), "done": item.group(1) != " ", "text": item.group(3).strip()}
            )
    return [g for g in groups if g["items"]]


def specs(src: Sources) -> list[dict[str, Any]]:
    result = []
    for spec in sorted(src.specs.glob("*/spec.md")):
        markdown = _read(spec)
        result.append(
            {
                "capability": spec.parent.name,
                "purpose": section(markdown, "Purpose"),
                "requirements": requirements_of(section(markdown, "Requirements")),
            }
        )
    return result


def pending_requirements(src: Sources) -> set[str]:
    """Requirements added or modified by changes not archived yet (for check mode)."""
    names = set()
    for spec in src.active.glob("*/specs/*/spec.md"):
        if spec.parts[-4] == "archive":
            continue
        for kind, found in delta_requirements(_read(spec)).items():
            if kind in ("added", "modified"):
                names |= {f"{spec.parent.name}: {n}" for n in found}
    return names


def decisions(src: Sources) -> list[dict[str, Any]]:
    result = []
    for path in sorted(src.decisions.glob("[0-9][0-9][0-9][0-9]-*.md")):
        markdown = _read(path)
        title = re.match(r"^# (\d{4}) — (.+)$", markdown, re.MULTILINE)
        meta = dict(re.findall(r"^- \*\*(\w+):\*\* (.+)$", markdown, re.MULTILINE))
        result.append(
            {
                "number": path.name[:4],
                "title": title.group(2).strip() if title else path.stem[5:],
                "date": meta.get("Date"),
                "status": meta.get("Status"),
                "markdown": markdown,
            }
        )
    return result


def tests(src: Sources) -> tuple[list[dict[str, Any]], dict[str, str | None]]:
    """Every test case from both reports, with the requirements it names."""
    found, reports = [], {}
    for suite, path in (("backend", src.backend_junit), ("frontend", src.frontend_junit)):
        if not path.is_file():
            reports[suite] = None
            continue
        root = ET.parse(path).getroot()
        stamps = [s.get("timestamp") for s in root.iter("testsuite") if s.get("timestamp")]
        reports[suite] = max(stamps) if stamps else None
        for case in root.iter("testcase"):
            name = case.get("name", "")
            if suite == "backend":
                links = [p.get("value") for p in case.iter("property") if p.get("name") == "spec"]
            else:
                tag = FRONTEND_TAG.match(name)
                links = [f"{tag.group(1)}: {tag.group(2)}"] if tag else []
                name = FRONTEND_TAG.sub("", name)
            if case.find("failure") is not None or case.find("error") is not None:
                status = "failed"
            elif case.find("skipped") is not None:
                status = "skipped"
            else:
                status = "passed"
            found.append(
                {
                    "suite": suite,
                    "id": f"{case.get('classname', '')}::{name}",
                    "status": status,
                    "seconds": float(case.get("time") or 0),
                    "requirements": links,
                }
            )
    return found, reports


# --- Joining -----------------------------------------------------------------------------


def requirement_status(linked: list[dict[str, Any]]) -> str:
    if not linked:
        return "untested"
    if any(t["status"] == "failed" for t in linked):
        return "failing"
    if all(t["status"] == "passed" for t in linked):
        return "verified"
    return "untested"  # only skipped tests: nothing actually verified it


def build(src: Sources) -> dict[str, Any]:
    all_tests, reports = tests(src)
    capabilities = specs(src)
    for capability in capabilities:
        for req in capability["requirements"]:
            key = f"{capability['capability']}: {req['name']}"
            linked = [
                {k: t[k] for k in ("suite", "id", "status", "seconds")}
                for t in all_tests
                if key in t["requirements"]
            ]
            req["tests"] = linked
            req["status"] = requirement_status(linked)
    statuses = [r["status"] for c in capabilities for r in c["requirements"]]
    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "reports": reports,
        "totals": {
            "changes": sum(1 for p in src.archive.iterdir() if p.is_dir()),
            "requirements": len(statuses),
            "verified": statuses.count("verified"),
            "tests": {
                suite: sum(1 for t in all_tests if t["suite"] == suite)
                for suite in ("backend", "frontend")
            },
            "linked_tests": sum(1 for t in all_tests if t["requirements"]),
        },
        "changes": changes(src),
        "specs": capabilities,
        "decisions": decisions(src),
    }


def problems(src: Sources, data: dict[str, Any]) -> list[str]:
    """What check mode reports: requirements not verified, and links to nothing."""
    known = {
        f"{c['capability']}: {r['name']}" for c in data["specs"] for r in c["requirements"]
    } | pending_requirements(src)
    found = []
    for capability in data["specs"]:
        for req in capability["requirements"]:
            if req["status"] != "verified":
                found.append(f"{req['status']}: {capability['capability']}: {req['name']}")
    all_tests, _ = tests(src)
    pending = pending_requirements(src)
    linked = {name for t in all_tests if t["status"] == "passed" for name in t["requirements"]}
    found += [f"untested (pending change): {name}" for name in sorted(pending - linked)]
    for test in all_tests:
        found += [
            f"unknown requirement {name!r} named by {test['suite']} test {test['id']}"
            for name in test["requirements"]
            if name not in known
        ]
    return found


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="scripts.walkthrough")
    parser.add_argument("--repo", type=Path, default=REPO)
    parser.add_argument("--backend-junit", type=Path)
    parser.add_argument("--frontend-junit", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--check", action="store_true", help="exit 1 on any coverage gap")
    args = parser.parse_args(argv)

    repo = args.repo.resolve()
    src = Sources.of(
        repo,
        args.backend_junit or repo / "backend" / "test-results" / "junit.xml",
        args.frontend_junit or repo / "frontend" / "test-results" / "junit.xml",
    )
    data = build(src)
    if args.check:
        found = problems(src, data)
        for problem in found:
            print(problem)
        totals = data["totals"]
        print(f"{totals['verified']}/{totals['requirements']} requirements verified")
        return 1 if found else 0

    out = args.out or repo / "frontend" / "content" / "walkthrough.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    totals = data["totals"]
    print(
        f"wrote {out}: {totals['changes']} changes, {totals['verified']}/{totals['requirements']} "
        f"requirements verified, {len(data['decisions'])} decisions"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
