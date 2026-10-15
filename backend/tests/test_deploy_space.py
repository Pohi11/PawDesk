"""Spec: demo-hosting, the deploy bundle (scripts/deploy_space.py)."""

import subprocess
from pathlib import Path

import pytest

from scripts.deploy_space import build_bundle

spec = pytest.mark.spec


def commit_all(repo: Path) -> None:
    for args in (["add", "-A"], ["commit", "-q", "-m", "files"]):
        subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@example.test", *args],
            cwd=repo,
            check=True,
        )


def files_under(root: Path) -> set[str]:
    return {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}


@spec("demo-hosting", "A deploy publishes only committed files")
def test_bundle_holds_committed_files_and_the_space_files(tmp_path):
    repo, bundle = tmp_path / "repo", tmp_path / "bundle"
    (repo / "deploy/huggingface").mkdir(parents=True)
    (repo / "backend").mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    (repo / ".gitignore").write_text(".env\nPLAN.md\n")
    (repo / "README.md").write_text("repository readme")
    (repo / "backend/app.py").write_text("print('hi')\n")
    (repo / "deploy/huggingface/Dockerfile").write_text("FROM scratch\n")
    (repo / "deploy/huggingface/README.md").write_text("---\nsdk: docker\n---\n")
    commit_all(repo)
    (repo / ".env").write_text("OPENROUTER_API_KEY=not-a-real-key\n")
    (repo / "PLAN.md").write_text("private")
    (repo / "untracked.txt").write_text("not committed")
    (repo / "backend/app.py").write_text("print('edited, not committed')\n")
    bundle.mkdir()

    build_bundle(repo, bundle)

    assert files_under(bundle) == {
        ".gitignore",
        "README.md",
        "Dockerfile",
        "backend/app.py",
        "deploy/huggingface/Dockerfile",
        "deploy/huggingface/README.md",
    }
    assert (bundle / "README.md").read_text() == "---\nsdk: docker\n---\n"
    assert (bundle / "Dockerfile").read_text() == "FROM scratch\n"
    assert (bundle / "backend/app.py").read_text() == "print('hi')\n"
