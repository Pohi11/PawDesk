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
    return commit


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
