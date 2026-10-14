"""Assemble the end-to-end test's screenshots into the README's demo GIF.

Run after `pnpm e2e` (from backend/):
    uv run python -m scripts.make_demo_gif
"""

from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parents[2]
FRAMES = REPO / "frontend" / "test-results" / "demo-frames"
OUT = REPO / "docs" / "demo.gif"
WIDTH = 960
SECONDS_PER_FRAME = 2.2


def main() -> None:
    paths = sorted(FRAMES.glob("*.png"))
    if not paths:
        raise SystemExit(f"no frames in {FRAMES}: run `pnpm e2e` in frontend/ first")
    frames = []
    for path in paths:
        image = Image.open(path).convert("RGB")
        height = round(image.height * WIDTH / image.width)
        frames.append(image.resize((WIDTH, height), Image.Resampling.LANCZOS).quantize(colors=128))
    OUT.parent.mkdir(exist_ok=True)
    frames[0].save(
        OUT,
        save_all=True,
        append_images=frames[1:],
        duration=int(SECONDS_PER_FRAME * 1000),
        loop=0,
        optimize=True,
    )
    print(f"wrote {OUT} ({len(frames)} frames, {OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
