"""Openly licensed photos for the guide pages, from Openverse (Wikimedia, Flickr...). Free; no key.

    uv run --with pillow python scripts/guide_stock.py search            # candidates + one review sheet per topic
    uv run --with pillow python scripts/guide_stock.py pick picks.json   # {"topic/slug": candidate number or null}

Only licences that allow commercial use (CC0, public domain, CC BY, CC BY-SA). Each photo's credit (creator,
licence, source) goes to web/public/guides/credits.json and is shown under the photo. Photos that already exist
(made earlier) are kept.
"""

import json
import re
import sys
import time
import urllib.parse
from pathlib import Path

import httpx
from PIL import Image, ImageDraw

from guide_images import OUT, PROMPTS, save_webp

WORK = Path(r"H:\Tools\tmp\guide_stock")
CREDITS = OUT / "credits.json"
HEADERS = {"User-Agent": "OrionGuides/0.1 (https://orionagentic.online)"}
API = "https://api.openverse.org/v1/images/"

# Search words per option (same keys as the photo prompts)
QUERIES = {
    "materials": {"100-cotton": "cotton fabric texture", "cotton-polyester-80-20": "fleece fabric texture",
                  "cotton-polyester-60-40": "knit fabric close up", "100-polyester": "polyester fabric",
                  "organic-cotton": "organic cotton", "recycled-polyester": "recycled polyester fabric",
                  "cotton-spandex": "stretch fabric"},
    "fabric_types": {"knitted-fleece": "fleece fabric", "french-terry": "terry cloth fabric", "jersey-knit": "jersey knit fabric",
                     "waffle-knit": "waffle knit fabric", "woven": "woven fabric texture"},
    "printing": {"screen-print": "screen printing shirt", "dtg-print": "direct to garment printing",
                 "embroidery": "embroidered logo", "heat-transfer": "heat press transfer", "no-logo": "plain hoodie"},
    "placement": {"front-left-chest": "polo shirt logo chest", "centre-chest-or-full-front": "printed hoodie front",
                  "back": "back print jacket", "sleeves": "sleeve patch", "hood": "hoodie hood"},
    "hoodie_types": {"pullover": "hoodie", "zip-up": "zip hoodie", "half-zip": "half zip pullover"},
    "collars": {"hooded": "hooded sweatshirt", "double-layer-hood": "hoodie hood", "crew-neck": "crewneck sweatshirt",
                "mock-neck": "mock neck", "funnel-neck": "funnel neck", "v-neck": "v-neck sweater"},
    "fit": {"regular": "hoodie", "loose-relaxed": "loose sweatshirt", "oversized": "oversized hoodie",
            "boxy": "boxy shirt", "slim": "slim fit shirt"},
    "design_details": {"plain": "plain sweatshirt", "cut-out": "cutout top", "distressed": "distressed clothing",
                       "colour-block": "color block jacket", "patchwork": "patchwork clothing", "raw-hem": "raw hem",
                       "side-slits": "side slit"},
    "length": {"regular": "sweatshirt", "crop": "crop top", "longline": "long hoodie"},
    "sleeves": {"regular": "sweater sleeve", "drop-shoulder": "drop shoulder", "raglan": "raglan sleeve",
                "batwing": "batwing sleeve"},
    "patterns": {"solid": "solid color fabric", "colour-block": "color block", "all-over-print": "printed fabric pattern",
                 "tie-dye": "tie-dye", "camouflage": "camouflage pattern", "striped": "striped fabric",
                 "graphic-or-letters": "graphic t-shirt"},
    "packaging": {"individual-polybag": "clothes plastic bag", "folded-with-tissue-paper": "tissue paper gift",
                  "on-a-hanger": "clothes hanger", "branded-box": "gift box clothing"},
    "gsm": {"160-200": "thin fabric", "200-240": "t-shirt fabric", "280-320": "sweatshirt fabric",
            "320-400": "thick fleece"},
    "drawstrings": {"flat-cotton": "hoodie drawstring", "round-cord": "drawstring cord", "no-drawstrings": "hoodie"},
    "pockets": {"kangaroo-pocket": "kangaroo pocket", "side-pockets": "jacket pockets", "no-pocket": "sweatshirt"},
    "labels": {"woven-neck-label": "clothing label", "printed-neck-label": "tagless label", "size-and-care-labels": "care label",
               "hang-tag": "hang tag"},
}
PER_OPTION = 4
CELL = 220


def thumb_url(result: dict) -> str:
    """A small version straight from the source, so the full original is never downloaded."""
    url = result["url"]
    if m := re.match(r"https://upload\.wikimedia\.org/wikipedia/commons/(\w/\w\w)/(.+)$", url):
        name = m.group(2)
        return f"https://upload.wikimedia.org/wikipedia/commons/thumb/{m.group(1)}/{name}/1024px-{name}" + (
            ".jpg" if name.lower().endswith((".tif", ".tiff")) else "")
    return url


def fetch(client: httpx.Client, url: str) -> bytes | None:
    try:
        r = client.get(url, timeout=60, follow_redirects=True)
        if r.status_code == 200 and len(r.content) < 15_000_000:
            return r.content
    except httpx.HTTPError:
        pass
    return None


def search() -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    found: dict[str, list[dict]] = {}
    with httpx.Client(headers=HEADERS) as client:
        for topic, options in QUERIES.items():
            rows = []
            for key, query in options.items():
                name = f"{topic}/{key}"
                if (OUT / f"{name}.webp").exists():
                    continue
                params = {"q": query, "license_type": "commercial", "page_size": 12, "mature": "false"}
                r = client.get(API + "?" + urllib.parse.urlencode(params), timeout=60)
                time.sleep(3.5)                                       # stay inside the anonymous rate limit
                results = [x for x in r.json().get("results", []) if (x.get("width") or 0) >= 600][:PER_OPTION] \
                    if r.status_code == 200 else []
                cands = []
                for i, res in enumerate(results):
                    data = fetch(client, thumb_url(res))
                    if not data:
                        continue
                    path = WORK / f"{topic}__{key}__{i}.jpg"
                    try:
                        Image.open(__import__("io").BytesIO(data)).convert("RGB").save(path, "JPEG", quality=85)
                    except Exception:
                        continue
                    cands.append({"n": i, "file": str(path), "title": res.get("title"), "creator": res.get("creator"),
                                  "license": res.get("license"), "license_version": res.get("license_version"),
                                  "license_url": res.get("license_url"), "source": res.get("foreign_landing_url"),
                                  "url": thumb_url(res)})
                found[name] = cands
                rows.append((name, cands))
                print(f"{name}: {len(cands)} candidates")
            if rows:
                sheet(topic, rows)
    (WORK / "candidates.json").write_text(json.dumps(found, ensure_ascii=False, indent=1), encoding="utf-8")


def sheet(topic: str, rows: list) -> None:
    """One review image per topic: a row per option, its candidates numbered."""
    img = Image.new("RGB", (200 + CELL * PER_OPTION, CELL * len(rows)), "white")
    draw = ImageDraw.Draw(img)
    for r, (name, cands) in enumerate(rows):
        draw.text((8, r * CELL + CELL // 2), name.split("/")[1], fill="black")
        for c in cands:
            tile = Image.open(c["file"])
            tile.thumbnail((CELL - 10, CELL - 10))
            x, y = 200 + c["n"] * CELL, r * CELL
            img.paste(tile, (x + 5, y + 5))
            draw.rectangle((x + 5, y + 5, x + 30, y + 25), fill="yellow")
            draw.text((x + 12, y + 8), str(c["n"]), fill="black")
    img.save(WORK / f"sheet_{topic}.jpg", "JPEG", quality=80)


def pick(picks_file: str) -> None:
    picks = json.loads(Path(picks_file).read_text(encoding="utf-8"))
    found = json.loads((WORK / "candidates.json").read_text(encoding="utf-8"))
    credits = json.loads(CREDITS.read_text(encoding="utf-8")) if CREDITS.exists() else {}
    for name, n in picks.items():
        if n is None:
            continue
        cand = next(c for c in found[name] if c["n"] == n)
        size = save_webp(Path(cand["file"]).read_bytes(), OUT / f"{name}.webp")
        licence = "Public domain" if cand["license"] in ("pdm", "cc0") else f"CC {cand['license'].upper()} {cand['license_version']}"
        credits[name] = {"creator": cand.get("creator") or "Unknown", "licence": licence,
                         "licence_url": cand.get("license_url"), "source": cand.get("source")}
        print(f"+ {name}  {size // 1024} KB  {licence}")
    CREDITS.write_text(json.dumps(credits, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    unknown = {f"{t}/{k}" for t, o in QUERIES.items() for k in o} - {f"{t}/{k}" for t, o in PROMPTS.items() for k in o}
    if unknown:
        sys.exit(f"queries for options with no photo slot: {sorted(unknown)}")
    if sys.argv[1:2] == ["search"]:
        search()
    elif sys.argv[1:2] == ["pick"] and len(sys.argv) == 3:
        pick(sys.argv[2])
    else:
        sys.exit(__doc__)
