"""Build the dashboard's pet photo set from Wikimedia Commons (spec: pet-photos).

Run from backend/:  uv run python -m scripts.fetch_pet_photos

Each pick names a Commons file by hand. The script reads its license and author from the
Commons API, refuses anything that is not CC0 or public domain, downloads a 640 px
thumbnail, center-crops it to 320 x 320, and re-encodes it as a JPEG with no EXIF or XMP,
so no camera, location, or author data is republished. It writes the photos to
frontend/public/pets/ and their manifest to frontend/lib/pet-photos.json. Both are
committed; this script runs by hand, never in CI.
"""

import html
import io
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import httpx
from PIL import Image, ImageOps

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
PHOTO_DIR = FRONTEND / "public" / "pets"
MANIFEST = FRONTEND / "lib" / "pet-photos.json"
API = "https://commons.wikimedia.org/w/api.php"
# Wikimedia asks every client to identify itself.
USER_AGENT = "PawDesk-photo-fetch/1.0 (synthetic pet care demo; one-off download)"
ALLOWED_LICENSES = {"cc0", "public domain"}
SIZE = 320
THUMB_WIDTH = 640


@dataclass(frozen=True)
class Pick:
    title: str  # "File:..." on Commons
    slug: str  # file name without extension
    species: str  # "dog" or "cat"
    breed: str | None  # None for a general photo of the species


@dataclass(frozen=True)
class Photo:
    file: str  # path the dashboard serves, e.g. "/pets/beagle.jpg"
    species: str
    breed: str | None
    source: str  # the Commons file page
    author: str
    license: str


class RefusedLicense(ValueError):
    pass


PICKS: tuple[Pick, ...] = (
    # One per seeded breed (scripts/seed.py).
    Pick("File:One Beagle Cute (2429819734).jpg", "beagle", "dog", "Beagle"),
    Pick(
        "File:Mountain dog looking at you.jpg",
        "bernese-mountain-dog",
        "dog",
        "Bernese Mountain Dog",
    ),
    Pick("File:Chihuahua 2.jpg", "chihuahua", "dog", "Chihuahua"),
    Pick(
        "File:Labrador Retriever (1210559).jpg",
        "labrador-retriever",
        "dog",
        "Labrador Retriever",
    ),
    Pick("File:Border Collie intense look.jpg", "border-collie", "dog", "Border Collie"),
    Pick(
        "File:Gracie.Day at the beach. (20539043889).jpg",
        "pembroke-welsh-corgi",
        "dog",
        "Pembroke Welsh Corgi",
    ),
    Pick("File:Tabby cat-3337027.jpg", "domestic-shorthair", "cat", "Domestic Shorthair"),
    Pick("File:Ragdoll cat resting (July 30, 2022).jpg", "ragdoll", "cat", "Ragdoll"),
    # General photos for pets whose breed has none here.
    Pick("File:BobbyWonderful.jpg", "dog-1", "dog", None),
    Pick("File:Langhaarchihuahua.jpg", "dog-2", "dog", None),
    Pick("File:Beagle-Harrier2.JPG", "dog-3", "dog", None),
    Pick("File:Orange tabby cat closeup.jpg", "cat-1", "cat", None),
    Pick("File:Cat portrait (Unsplash).jpg", "cat-2", "cat", None),
)


def _plain(value: str) -> str:
    """Commons metadata values are HTML fragments."""
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", value)).split())


def describe(pick: Pick, page: dict) -> tuple[Photo, str]:
    """The manifest entry and thumbnail URL for one API page, or RefusedLicense."""
    info = page["imageinfo"][0]
    meta = info.get("extmetadata", {})
    license_name = _plain(meta.get("LicenseShortName", {}).get("value", ""))
    if license_name.lower() not in ALLOWED_LICENSES:
        raise RefusedLicense(f"{pick.title}: license {license_name!r} is not CC0 or public domain")
    photo = Photo(
        file=f"/pets/{pick.slug}.jpg",
        species=pick.species,
        breed=pick.breed,
        source=info["descriptionurl"],
        author=_plain(meta.get("Artist", {}).get("value", "")) or "Unknown",
        license=license_name,
    )
    return photo, info["thumburl"]


def metadata_segments(data: bytes) -> list[str]:
    """The EXIF and XMP blocks in a JPEG. Both travel in APP1 segments, named by a prefix."""
    found, i = [], 2  # skip the start-of-image marker
    while i + 4 <= len(data) and data[i] == 0xFF:
        marker, length = data[i + 1], int.from_bytes(data[i + 2 : i + 4], "big")
        if marker == 0xDA:  # start of scan: only image data follows
            break
        payload = data[i + 4 : i + 2 + length]
        if marker == 0xE1 and payload.startswith(b"Exif\0"):
            found.append("exif")
        elif marker == 0xE1 and payload.startswith(b"http://ns.adobe.com/xap/1.0/\0"):
            found.append("xmp")
        i += 2 + length
    return found


def square(data: bytes, size: int = SIZE) -> bytes:
    """Center-crop to a square and re-encode as a JPEG that carries pixels only."""
    with Image.open(io.BytesIO(data)) as source:
        upright = ImageOps.exif_transpose(source)  # apply the camera's rotation first
        fitted = ImageOps.fit(upright.convert("RGB"), (size, size), Image.Resampling.LANCZOS)
    clean = Image.new("RGB", fitted.size)  # a fresh image has no info to carry over
    clean.paste(fitted)
    out = io.BytesIO()
    clean.save(out, "JPEG", quality=85, optimize=True, progressive=True)
    return out.getvalue()


def fetch(client: httpx.Client, picks: tuple[Pick, ...]) -> list[tuple[Photo, bytes]]:
    """Look up every pick, refuse the whole run on any bad license, then download."""
    response = client.get(
        API,
        params={
            "action": "query",
            "titles": "|".join(p.title for p in picks),
            "prop": "imageinfo",
            "iiprop": "url|extmetadata",
            "iiextmetadatafilter": "LicenseShortName|Artist",
            "iiurlwidth": THUMB_WIDTH,
            "format": "json",
            "formatversion": 2,
        },
    )
    response.raise_for_status()
    pages = {page["title"]: page for page in response.json()["query"]["pages"]}
    missing = [p.title for p in picks if "imageinfo" not in pages.get(p.title, {})]
    if missing:
        raise LookupError(f"not found on Commons: {missing}")
    described = [(pick, *describe(pick, pages[pick.title])) for pick in picks]
    result = []
    for _, photo, thumb in described:
        image = client.get(thumb)
        image.raise_for_status()
        data = square(image.content)
        if metadata_segments(data):
            raise AssertionError(f"{photo.file} still carries metadata")
        result.append((photo, data))
    return result


def write(photos: list[tuple[Photo, bytes]]) -> None:
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    for old in PHOTO_DIR.glob("*.jpg"):
        old.unlink()
    for photo, data in photos:
        (PHOTO_DIR / Path(photo.file).name).write_bytes(data)
    manifest = [asdict(photo) for photo, _ in photos]
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    if len({p.slug for p in PICKS}) != len(PICKS):
        raise ValueError("every pick needs its own slug")
    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=30, follow_redirects=True) as c:
        photos = fetch(c, PICKS)
    write(photos)
    total = sum(len(data) for _, data in photos)
    print(f"wrote {len(photos)} photos ({total / 1024:.0f} KB) and {MANIFEST.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
