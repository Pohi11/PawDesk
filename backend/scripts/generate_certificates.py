"""Generate the synthetic vaccine-certificate benchmark (spec: certificate-evaluation).

Run from backend/:  uv run python -m scripts.generate_certificates

Ground truth comes first, from a seeded RNG (pure, unit-tested). Each certificate is then
rendered from an HTML template with headless Chromium and post-processed with Pillow (blur,
rotation). Every clinic, vet, and pet is fictional, and every image says it is a synthetic
test document. The generated PNGs and truth.json are committed: they are the benchmark.
"""

import asyncio
import base64
import functools
import html
import json
import random
from datetime import date, timedelta
from pathlib import Path
from typing import Any

CERT_DIR = Path(__file__).resolve().parents[1] / "evals" / "certificates"
IMAGES_DIR = CERT_DIR / "images"
TRUTH_FILE = CERT_DIR / "truth.json"
FONTS_DIR = CERT_DIR / "fonts"

SEED = 2027
TODAY = date(2027, 3, 3)
# Reference stay for decision agreement: boarding, a week from "today".
STAY_START, STAY_END = TODAY + timedelta(days=7), TODAY + timedelta(days=10)

LAYOUTS = ("table", "tag", "card")
VARIANTS = ("clean", "blur", "rotate", "handwriting", "missing_expiry", "alias")
WATERMARK = "SYNTHETIC TEST DOCUMENT — NOT A REAL RECORD"

# All fictional.
CLINICS = [
    "Maple Hollow Veterinary Clinic",
    "Bramblewood Animal Hospital",
    "Cedar Bend Vet Care",
    "Larkspur Pet Clinic",
    "Quillfeather Veterinary Group",
    "Thistledown Animal Clinic",
]
VETS = [
    "Dr. Imogen Vale",
    "Dr. Rafael Quint",
    "Dr. Ada Morrow",
    "Dr. Tobias Wren",
    "Dr. Priya Holloway",
    "Dr. Felix Oduya",
]
DOG_NAMES = [
    "Biscuit",
    "Juniper",
    "Pepper",
    "Moose",
    "Rosie",
    "Waffles",
    "Clover",
    "Pickle",
    "Bramble",
    "Nugget",
    "Maple",
    "Tater",
]
CAT_NAMES = ["Olive", "Tofu", "Miso", "Pumpkin", "Fig", "Mochi", "Sprout", "Juno"]

# (vaccine, canonical label, alias labels, validity choices in days)
DOG_VACCINES = [
    ("rabies", "Rabies", ["Rabies (3 yr)", "Rabies 1-Year"], [365, 1095]),
    ("dhpp", "DHPP", ["DA2PP", "DAPP"], [365]),
    (
        "bordetella",
        "Bordetella",
        ["Kennel Cough (Bordetella)", "Bordetella bronchiseptica"],
        [182, 365],
    ),
]
DOG_OPTIONAL = [
    ("canine_influenza", "Canine Influenza", ["CIV H3N2/H3N8", "Canine Flu (H3N2)"], [365]),
    ("leptospirosis", "Leptospirosis", ["Lepto 4-way", "Lepto"], [365]),
]
CAT_VACCINES = [
    ("rabies", "Rabies", ["Rabies (Feline, 1 yr)", "Rabies 3-Year"], [365, 1095]),
    ("fvrcp", "FVRCP", ["Feline Distemper (FVRCP)", "FVRCP combo"], [365, 1095]),
]
CAT_OPTIONAL = [("felv", "FeLV", ["Feline Leukemia (FeLV)", "FeLV vaccine"], [365])]

DATE_FORMATS = ["%m/%d/%Y", "%b %d, %Y", "%d %b %Y"]


def _assign(n: int, rng: random.Random) -> list[tuple[str, str]]:
    """Each layout gets n/3 certificates; variants cycle so each appears n/6 times."""
    pairs = [(LAYOUTS[i % 3], VARIANTS[(i // 3) % len(VARIANTS)]) for i in range(n)]
    rng.shuffle(pairs)
    return pairs


def _expiry_for(rng: random.Random, given: date, validity_days: int) -> date:
    """Mostly normal expiries; some land right on the reference stay's boundaries so a
    one-day reading error would change the compliance decision."""
    roll = rng.random()
    if roll < 0.18:
        return STAY_END + timedelta(days=rng.choice([-1, 0, 1]))  # boundary cases
    if roll < 0.30:
        return TODAY - timedelta(days=rng.randint(5, 120))  # already expired
    return given + timedelta(days=validity_days)


def make_truth(seed: int = SEED, n: int = 36) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    certificates = []
    for i, (layout, variant) in enumerate(_assign(n, rng), start=1):
        species = "dog" if rng.random() < 0.65 else "cat"
        core, optional = (
            (DOG_VACCINES, DOG_OPTIONAL) if species == "dog" else (CAT_VACCINES, CAT_OPTIONAL)
        )
        chosen = list(core) + [v for v in optional if rng.random() < 0.4]
        records = []
        for vaccine, label, aliases, validities in chosen:
            given = TODAY - timedelta(days=rng.randint(20, 700))
            expires = _expiry_for(rng, given, rng.choice(validities))
            if expires < given:  # an "already expired" pick that predates the shot
                given = expires - timedelta(days=rng.choice(validities))
            records.append(
                {
                    "label": rng.choice(aliases) if variant == "alias" else label,
                    "vaccine": vaccine,
                    "administered_on": given.isoformat(),
                    "expires_on": expires.isoformat(),
                }
            )
        if variant == "missing_expiry":
            records[rng.randrange(len(records))]["expires_on"] = None
        certificates.append(
            {
                "id": f"cert-{i:02d}",
                "file": f"images/cert-{i:02d}.png",
                "layout": layout,
                "variant": variant,
                "species": species,
                "pet_name": rng.choice(DOG_NAMES if species == "dog" else CAT_NAMES),
                "owner": rng.choice(
                    ["A. Lindqvist", "M. Okafor", "P. Venkataraman", "J. Whitfield", "S. Calloway"]
                ),
                "clinic": rng.choice(CLINICS),
                "vet": rng.choice(VETS),
                "date_format": rng.choice(DATE_FORMATS),
                "records": records,
            }
        )
    return certificates


# --- Rendering ------------------------------------------------------------------------

_FONTS = {
    "Hand": "Caveat.ttf",
    "Scrawl": "ReenieBeanie.ttf",
    "Typewriter": "CourierPrime-Regular.ttf",
}


@functools.cache
def _font_faces() -> str:
    """Fonts embedded as data URLs: a page loaded with set_content() can't fetch file://
    fonts (it silently falls back to whatever the OS has), and embedding keeps rendering
    independent of the machine."""
    faces = []
    for family, file in _FONTS.items():
        b64 = base64.b64encode((FONTS_DIR / file).read_bytes()).decode()
        faces.append(
            f"@font-face {{ font-family: '{family}'; src: url(data:font/ttf;base64,{b64}); }}"
        )
    return "\n".join(faces)


_BASE_CSS = """
body { margin: 0; background: #fff; }
#cert { width: 780px; padding: 28px 34px; box-sizing: border-box; color: #1d1d1f;
        font-family: {body_font}; position: relative; background: {paper}; }
.mark { position: absolute; top: 46%; left: -10px; right: -10px; text-align: center;
        transform: rotate(-12deg); font: 700 26px Arial, sans-serif; color: rgba(200,0,0,.22);
        letter-spacing: 2px; pointer-events: none; }
.foot { margin-top: 14px; font: 11px Arial, sans-serif; color: #a00; }
h1 { margin: 0 0 4px; font-size: 22px; } .sub { font-size: 13px; color: #555; }
table { width: 100%; border-collapse: collapse; margin-top: 14px; font-size: 15px; }
th, td { border: 1px solid #999; padding: 6px 8px; text-align: left; }
.hw { font-family: 'Hand', cursive; font-size: 21px; color: #1b2a6b; }
.scrawl { font-family: 'Scrawl', cursive; font-size: 24px; color: #222; }
.tag { border: 3px double #444; border-radius: 10px; padding: 14px 18px; margin-top: 10px; }
.row { display: flex; gap: 16px; margin: 6px 0; font-size: 15px; }
.row b { width: 130px; display: inline-block; }
.card { border: 2px solid #6b7f4a; border-radius: 6px; padding: 12px; background: #fbf8ec; }
.line { border-bottom: 1px dotted #888; padding: 6px 2px; display: flex; gap: 18px; }
"""


def _fmt(iso: str | None, fmt: str) -> str:
    return date.fromisoformat(iso).strftime(fmt) if iso else ""


def render_html(cert: dict[str, Any]) -> str:
    e = html.escape
    hand = cert["variant"] == "handwriting" or cert["layout"] == "card"
    value_class = ("scrawl" if cert["variant"] == "handwriting" else "hw") if hand else ""
    fmt = cert["date_format"]
    css = _font_faces() + _BASE_CSS.replace(
        "{body_font}", "'Typewriter', monospace" if cert["layout"] == "tag" else "Arial, sans-serif"
    ).replace("{paper}", "#fffef9" if cert["layout"] == "card" else "#ffffff")

    def v(text: str) -> str:
        return f'<span class="{value_class}">{e(text)}</span>'

    header = (
        f"<h1>{e(cert['clinic'])}</h1>"
        f"<div class='sub'>Vaccination Certificate · {e(cert['vet'])}</div>"
        f"<div class='row'><b>Patient</b>{v(cert['pet_name'])}"
        f"<b>Species</b>{v(cert['species'].title())}</div>"
        f"<div class='row'><b>Owner</b>{v(cert['owner'])}</div>"
    )
    recs = cert["records"]
    if cert["layout"] == "table":
        rows = "".join(
            f"<tr><td>{v(r['label'])}</td><td>{v(_fmt(r['administered_on'], fmt))}</td>"
            f"<td>{v(_fmt(r['expires_on'], fmt))}</td></tr>"
            for r in recs
        )
        body = f"<table><tr><th>Vaccine</th><th>Date Given</th><th>Expires</th></tr>{rows}</table>"
    elif cert["layout"] == "tag":
        body = "".join(
            f"<div class='tag'><div class='row'><b>VACCINE</b>{v(r['label'])}</div>"
            f"<div class='row'><b>ADMINISTERED</b>{v(_fmt(r['administered_on'], fmt))}</div>"
            f"<div class='row'><b>VALID UNTIL</b>{v(_fmt(r['expires_on'], fmt) or '—')}</div></div>"
            for r in recs
        )
    else:  # card
        body = (
            "<div class='card'>"
            + "".join(
                f"<div class='line'><span>{v(r['label'])}</span><span>given {v(_fmt(r['administered_on'], fmt))}</span>"
                f"<span>{'due ' + v(_fmt(r['expires_on'], fmt)) if r['expires_on'] else ''}</span></div>"
                for r in recs
            )
            + "</div>"
        )
    return (
        f"<!doctype html><html><head><meta charset='utf-8'><style>{css}</style></head>"
        f"<body><div id='cert'>{header}{body}<div class='mark'>{WATERMARK}</div>"
        f"<div class='foot'>{WATERMARK} · fictional clinic, veterinarian, and pet.</div>"
        f"</div></body></html>"
    )


def _post_process(path: Path, variant: str, rng: random.Random) -> None:
    from PIL import Image, ImageFilter

    if variant == "blur":
        with Image.open(path) as im:
            im.filter(ImageFilter.GaussianBlur(radius=rng.uniform(1.4, 2.0))).save(path)
    elif variant == "rotate":
        angle = rng.choice([-1, 1]) * rng.uniform(3, 7)
        with Image.open(path) as im:
            im.convert("RGB").rotate(angle, expand=True, fillcolor="white").save(path)


async def render_all(certificates: list[dict[str, Any]]) -> None:
    from playwright.async_api import async_playwright

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED + 1)
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(
            viewport={"width": 860, "height": 1200}, device_scale_factor=1
        )
        for cert in certificates:
            await page.set_content(render_html(cert), wait_until="load")
            await page.evaluate("document.fonts.ready")
            out = CERT_DIR / cert["file"]
            await page.locator("#cert").screenshot(path=str(out))
            _post_process(out, cert["variant"], rng)
        await browser.close()


def main() -> None:
    certificates = make_truth()
    asyncio.run(render_all(certificates))
    truth = {
        "seed": SEED,
        "today": TODAY.isoformat(),
        "reference_stay": {
            "service": "boarding",
            "start": STAY_START.isoformat(),
            "end": STAY_END.isoformat(),
        },
        "certificates": certificates,
    }
    TRUTH_FILE.write_text(json.dumps(truth, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(certificates)} certificates to {IMAGES_DIR} and {TRUTH_FILE.name}")


if __name__ == "__main__":
    main()
