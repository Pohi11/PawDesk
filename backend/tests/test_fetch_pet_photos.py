"""Spec: pet-photos (the fetch script). No network: Commons is a mock transport."""

import io

import httpx
import pytest
from PIL import Image

from scripts.fetch_pet_photos import (
    API,
    Pick,
    RefusedLicense,
    describe,
    fetch,
    metadata_segments,
    square,
)

spec = pytest.mark.spec
LICENSED = "Every committed photo is licensed for reuse and recorded"
NO_METADATA = "Committed photos carry no embedded metadata"

RED, GREEN, BLUE = (255, 0, 0), (0, 255, 0), (0, 0, 255)
XMP = b"http://ns.adobe.com/xap/1.0/\0<x:xmpmeta><dc:creator>Someone</dc:creator></x:xmpmeta>"
BEAGLE = Pick("File:A beagle.jpg", "beagle", "dog", "Beagle")


def jpeg(image: Image.Image, orientation: int | None = None, xmp: bool = True) -> bytes:
    """A JPEG carrying EXIF (with a GPS position) and, optionally, an XMP block."""
    exif = Image.Exif()
    exif[0x8825] = {2: (41.0, 52.0, 30.0), 1: "N"}  # GPSInfo: latitude
    if orientation:
        exif[0x0112] = orientation
    out = io.BytesIO()
    image.save(out, "JPEG", exif=exif)
    data = out.getvalue()
    if not xmp:
        return data
    segment = b"\xff\xe1" + (len(XMP) + 2).to_bytes(2, "big") + XMP
    return data[:2] + segment + data[2:]


def colour(data: bytes, xy: tuple[int, int]) -> tuple[int, int, int]:
    with Image.open(io.BytesIO(data)) as image:
        return image.convert("RGB").getpixel(xy)


def near(actual, expected, tolerance=40) -> bool:
    return all(abs(a - e) <= tolerance for a, e in zip(actual, expected, strict=True))


def commons(license_name: str = "CC0", artist: str = "<a href='/u'>Jo &amp; Sam</a>"):
    """A scripted Commons: the API answers for any title, thumbnails are a green square."""
    seen: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        if str(request.url).startswith(API):
            titles = request.url.params["titles"].split("|")
            pages = [
                {
                    "title": title,
                    "imageinfo": [
                        {
                            "descriptionurl": f"https://commons.wikimedia.org/wiki/{title}",
                            "thumburl": f"https://upload.wikimedia.org/thumb/{i}.jpg",
                            "extmetadata": {
                                "LicenseShortName": {"value": license_name},
                                "Artist": {"value": artist},
                            },
                        }
                    ],
                }
                for i, title in enumerate(titles)
            ]
            return httpx.Response(200, json={"query": {"pages": pages}})
        return httpx.Response(200, content=jpeg(Image.new("RGB", (640, 480), GREEN)))

    return httpx.Client(transport=httpx.MockTransport(handle)), seen


@spec("pet-photos", NO_METADATA)
def test_square_drops_exif_and_xmp():
    source = jpeg(Image.new("RGB", (800, 400), GREEN))
    assert metadata_segments(source) == ["xmp", "exif"]

    result = square(source)

    assert metadata_segments(result) == []
    assert b"Someone" not in result
    with Image.open(io.BytesIO(result)) as image:
        assert (image.format, image.size) == ("JPEG", (320, 320))


def test_square_keeps_the_centre():
    image = Image.new("RGB", (800, 400), BLUE)
    image.paste(GREEN, (200, 0, 600, 400))

    result = square(jpeg(image))

    assert all(near(colour(result, xy), GREEN) for xy in [(5, 5), (160, 160), (314, 314)])


def test_square_applies_the_camera_rotation_before_dropping_it():
    # Stored landscape, left red and right blue; orientation 6 means "turn 90 degrees
    # clockwise to display", so the upright picture has red on top and blue below.
    image = Image.new("RGB", (400, 200), BLUE)
    image.paste(RED, (0, 0, 200, 200))

    result = square(jpeg(image, orientation=6, xmp=False))

    assert near(colour(result, (160, 40)), RED)
    assert near(colour(result, (160, 280)), BLUE)


@spec("pet-photos", LICENSED)
def test_describe_records_source_author_and_license():
    client, _ = commons()
    page = client.get(API, params={"titles": BEAGLE.title}).json()["query"]["pages"][0]

    photo, thumb = describe(BEAGLE, page)

    assert photo.file == "/pets/beagle.jpg"
    assert (photo.species, photo.breed, photo.license) == ("dog", "Beagle", "CC0")
    assert photo.source == "https://commons.wikimedia.org/wiki/File:A beagle.jpg"
    assert photo.author == "Jo & Sam"  # HTML removed
    assert thumb.startswith("https://upload.wikimedia.org/")


@spec("pet-photos", LICENSED)
@pytest.mark.parametrize("license_name", ["CC BY-SA 4.0", "CC BY 2.0", ""])
def test_any_other_license_refuses_the_whole_run_before_downloading(license_name):
    client, seen = commons(license_name)

    with pytest.raises(RefusedLicense):
        fetch(client, (BEAGLE, Pick("File:Cat.jpg", "cat", "cat", None)))

    assert all(url.startswith(API) for url in seen)  # no thumbnail was downloaded


@spec("pet-photos", LICENSED)
@spec("pet-photos", NO_METADATA)
@pytest.mark.parametrize("license_name", ["CC0", "Public domain"])
def test_fetch_returns_clean_photos(license_name):
    client, _ = commons(license_name)

    [(photo, data)] = fetch(client, (BEAGLE,))

    assert photo.license == license_name
    assert metadata_segments(data) == []


def test_unknown_title_is_an_error():
    def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"query": {"pages": [{"title": BEAGLE.title}]}})

    with pytest.raises(LookupError, match="not found"):
        fetch(httpx.Client(transport=httpx.MockTransport(handle)), (BEAGLE,))
