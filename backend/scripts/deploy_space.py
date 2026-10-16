"""Deploy the public demo to a Hugging Face Space (spec: demo-hosting; decision record 0019).

Run from backend/:  uv run python -m scripts.deploy_space <owner>/<space>

The bundle is built from the commit at HEAD with `git archive`, never from the working tree,
so uncommitted files, ignored files (.env), and private notes can't be uploaded. The Space's
own Dockerfile and README replace the repository's root ones: Hugging Face reads a Space's
settings from its README's front matter. Secrets are set on the Space, never in the bundle.
"""

import io
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SPACE_FILES = Path("deploy/huggingface")
# Folders the bundle owns on the Space: files deleted from them in the repo are deleted
# there too. The Space's own .gitattributes is left alone.
OWNED = ["backend/**", "frontend/**", "openspec/**", "docs/**", "deploy/**"]


def build_bundle(repo: Path, dest: Path) -> str:
    """Write the files committed at HEAD to `dest`, with the Space's Dockerfile and README at
    its root. Returns the commit it was built from."""
    commit = git(repo, "rev-parse", "HEAD").strip()
    archive = subprocess.run(
        ["git", "archive", "--format=tar", commit], cwd=repo, check=True, capture_output=True
    ).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(dest, filter="data")
    for name in ("Dockerfile", "README.md"):
        shutil.copyfile(dest / SPACE_FILES / name, dest / name)
    mark_binaries_for_lfs(dest)
    return commit


def mark_binaries_for_lfs(bundle: Path) -> None:
    """Add an LFS rule for each extension that has a binary file in the bundle.

    The Hub stores larger binaries (such as the card fonts) in LFS, and the Space's build only
    resolves files its .gitattributes marks for LFS; without a rule it checks out the pointer
    (change space-binary-files, D1). Files kept as plain git pass through git-lfs unchanged.
    """
    extensions = sorted(
        {p.suffix.lower() for p in bundle.rglob("*") if p.is_file() and p.suffix and _binary(p)}
    )
    if not extensions:
        return
    attributes = bundle / ".gitattributes"
    existing = attributes.read_text(encoding="utf-8") if attributes.is_file() else ""
    if existing and not existing.endswith("\n"):
        existing += "\n"
    rules = [f"*{ext} filter=lfs diff=lfs merge=lfs -text" for ext in extensions]
    lines = ["# Binary files the Hub may store in LFS (scripts/deploy_space.py).", *rules]
    attributes.write_text(existing + "\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def _binary(path: Path) -> bool:
    """Git's test for binary content: a NUL byte in the first 8,000 bytes."""
    with path.open("rb") as f:
        return b"\0" in f.read(8000)


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout


def main() -> None:
    if len(sys.argv) != 2 or "/" not in sys.argv[1]:
        sys.exit("usage: python -m scripts.deploy_space <owner>/<space>")
    space = sys.argv[1]
    if git(REPO_ROOT, "status", "--porcelain", "--untracked-files=no"):
        print("deploy: uncommitted changes are not deployed; deploying HEAD", file=sys.stderr)
    with tempfile.TemporaryDirectory() as tmp:
        commit = build_bundle(REPO_ROOT, Path(tmp))
        delete = [arg for pattern in OWNED for arg in ("--delete", pattern)]
        subprocess.run(
            ["hf", "upload", space, tmp, ".", "--repo-type", "space", *delete,
             "--commit-message", f"Deploy {commit[:12]}"],
            check=True,
        )  # fmt: skip
    print(f"deployed {commit[:12]} to https://huggingface.co/spaces/{space}")


if __name__ == "__main__":
    main()
