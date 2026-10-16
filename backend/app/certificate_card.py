"""Draw a generated request's vaccine certificate as a PNG (spec: demo-generator, design D4).

Drawn by code with Pillow and the project's bundled open fonts, so the API needs no browser.
The same request always gives the same bytes.
"""

import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from PIL.PngImagePlugin import PngInfo

from app.demo_generator import GeneratedRequest, printed

FONTS = Path(__file__).resolve().parents[1] / "evals" / "certificates" / "fonts"
WIDTH, HEIGHT = 1000, 680
INK = (26, 35, 56)
FAINT = (110, 120, 135)
RULE = (200, 206, 198)
PAPER = (252, 251, 247)
ACCENT = (31, 111, 85)
SYNTHETIC = (
    "Synthetic PawDesk demo certificate. The pet, owner, clinic, and veterinarian are fictional."
)


def _font(size: int, name: str | None = None) -> ImageFont.FreeTypeFont:
    # Basic layout even where Raqm is installed: Raqm shapes the Caveat signature differently,
    # and the committed sample cards must match a fresh drawing on every machine (change
    # basic-text-layout, D1). load_default always uses basic layout.
    if name:
        return ImageFont.truetype(str(FONTS / name), size, layout_engine=ImageFont.Layout.BASIC)
    return ImageFont.load_default(size=size)


def render(request: GeneratedRequest) -> bytes:
    image = Image.new("RGB", (WIDTH, HEIGHT), PAPER)
    draw = ImageDraw.Draw(image)
    heading, label, value = _font(30), _font(17), _font(20, "CourierPrime-Regular.ttf")

    # Header band with the clinic.
    draw.rectangle([0, 0, WIDTH, 92], fill=ACCENT)
    draw.text((40, 22), request.clinic, font=_font(30), fill=(255, 255, 255))
    draw.text((40, 60), "Veterinary services", font=_font(16), fill=(214, 236, 226))
    draw.text((40, 118), "Certificate of Vaccination", font=heading, fill=INK)

    # Patient and owner.
    y = 172
    # Species and breed get the widest column; Owner lines up with the Expires column.
    for x, (name, text) in zip(
        (40, 300, 680),
        [
            ("Patient", request.pet),
            ("Species", f"{request.species.capitalize()}, {request.breed}"),
            ("Owner", request.owner),
        ],
        strict=True,
    ):
        draw.text((x, y), name, font=label, fill=FAINT)
        draw.text((x, y + 24), text, font=value, fill=INK)

    # The records table.
    y = 262
    columns = [("Vaccine", 40), ("Date given", 400), ("Expires", 680)]
    for name, x in columns:
        draw.text((x, y), name, font=label, fill=FAINT)
    draw.line([40, y + 30, WIDTH - 40, y + 30], fill=RULE, width=2)
    y += 44
    for record in request.records:
        draw.text((40, y), record.label, font=value, fill=INK)
        draw.text((400, y), printed(record.administered_on), font=value, fill=INK)
        draw.text((680, y), printed(record.expires_on), font=value, fill=INK)
        y += 40
        draw.line([40, y - 8, WIDTH - 40, y - 8], fill=(232, 236, 230), width=1)

    # Signature. Nothing below it: the records step reads every line, and a line saying the
    # card isn't real is rightly a reason for doubt (change card-synthetic-marking, D1).
    draw.text((40, HEIGHT - 128), request.vet, font=_font(40, "Caveat.ttf"), fill=(40, 60, 120))
    draw.line([40, HEIGHT - 80, 380, HEIGHT - 80], fill=RULE, width=2)
    draw.text((40, HEIGHT - 72), "Attending veterinarian", font=label, fill=FAINT)

    # The synthetic marking travels in the file's metadata, which the model never sees (D2).
    info = PngInfo()
    info.add_text("Comment", SYNTHETIC)
    out = io.BytesIO()
    image.save(out, format="PNG", optimize=True, pnginfo=info)
    return out.getvalue()
