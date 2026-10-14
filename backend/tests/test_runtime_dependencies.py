"""The production image installs only runtime dependencies (`uv sync --no-dev`), so every
third-party package the app imports must be declared as one, not merely present because a
dev tool or another package happens to pull it in."""

import ast
import re
import sys
import tomllib
from importlib import metadata
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]


def imported_top_level(package: Path) -> set[str]:
    names = set()
    for path in package.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                names |= {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names.add(node.module.split(".")[0])
    return names


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


@pytest.mark.spec("delivery-pipeline", "Every change is checked automatically")
def test_every_imported_package_is_a_declared_runtime_dependency():
    project = tomllib.loads((BACKEND / "pyproject.toml").read_text(encoding="utf-8"))
    declared = {
        normalize(re.split(r"[\[<>=!~ ;]", requirement, maxsplit=1)[0])
        for requirement in project["project"]["dependencies"]
    }
    distributions = metadata.packages_distributions()
    third_party = imported_top_level(BACKEND / "app") - set(sys.stdlib_module_names) - {"app"}

    missing = {
        module: distributions.get(module, ["?"])
        for module in sorted(third_party)
        if not any(normalize(d) in declared for d in distributions.get(module, []))
    }

    assert missing == {}, f"imported by app/ but not declared as runtime dependencies: {missing}"
