"""Fail if any tracked file holds a value shaped like a real model-provider key
(spec: delivery-pipeline). CI also runs a full secret scanner over the history; this is
the fast check that runs with the test suite.

    uv run python -m scripts.secret_scan     # exit 1 and list findings, or exit 0
"""

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
KEY_SHAPES = [
    re.compile(r"sk-or-v1-[0-9a-f]{40,}"),  # OpenRouter
    re.compile(r"sk-proj-[A-Za-z0-9_-]{40,}"),  # OpenAI project keys
    re.compile(r"sk-ant-[A-Za-z0-9_-]{40,}"),  # Anthropic
]


def tracked_files(repo: Path) -> list[Path]:
    out = subprocess.run(
        ["git", "-C", str(repo), "ls-files", "-z"], capture_output=True, check=True
    ).stdout
    return [repo / name for name in out.decode().split("\0") if name]


def find_secrets(repo: Path) -> list[str]:
    findings = []
    for path in tracked_files(repo):
        if not path.is_file():
            continue
        text = path.read_bytes().decode("utf-8", errors="ignore")
        for shape in KEY_SHAPES:
            for match in shape.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                findings.append(
                    f"{path.relative_to(repo).as_posix()}:{line}: {match.group(0)[:12]}…"
                )
    return findings


def main() -> int:
    findings = find_secrets(REPO)
    for finding in findings:
        print(finding)
    print("no key-shaped values in tracked files" if not findings else f"{len(findings)} found")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
