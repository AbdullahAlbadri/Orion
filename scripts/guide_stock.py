"""Openly licensed photos for the guide pages, from Openverse (Wikimedia, Flickr...). Free; no key.

    uv run --with pillow python scripts/guide_stock.py search            # candidates + one review sheet per topic
    uv run --with pillow python scripts/guide_stock.py commons           # the same from Wikimedia Commons, 8 per option
    uv run --with pillow python scripts/guide_stock.py pick picks.json   # {"topic/slug": candidate number or null}

Only licences that allow commercial use (CC0, public domain, CC BY, CC BY-SA). Each photo's credit (creator,
licence, source) goes to web/public/guides/credits.json and is shown under the photo. Photos that already exist
(made earlier) are kept.
"""

import io
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


def sheet(topic: str, rows: list, columns: int = PER_OPTION, cell: int = CELL) -> None:
    """One review image per topic: a row per option, its candidates numbered."""
    CELL = cell  # noqa: N806
    img = Image.new("RGB", (200 + CELL * columns, CELL * len(rows)), "white")
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
        if "licence" in cand:                                         # Wikimedia gives the licence name as is
            licence = cand["licence"]
        else:
            licence = "Public domain" if cand["license"] in ("pdm", "cc0") else f"CC {cand['license'].upper()} {cand['license_version']}"
        credits[name] = {"creator": cand.get("creator") or "Unknown", "licence": licence,
                         "licence_url": cand.get("license_url"), "source": cand.get("source")}
        print(f"+ {name}  {size // 1024} KB  {licence}")
    CREDITS.write_text(json.dumps(credits, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")


# --- Wikimedia Commons (everything there is free for commercial use, with credit) -------------------------

COMMONS = "https://commons.wikimedia.org/w/api.php"
# Several searches per option; the first ones are the most precise
COMMONS_QUERIES = {
    "materials": {"cotton-polyester-60-40": ["cotton polyester fabric", "sweatshirt fabric"],
                  "recycled-polyester": ["recycled polyester", "recycled PET fabric"],
                  "cotton-spandex": ["elastane fabric", "stretch fabric", "spandex"]},
    "fabric_types": {"french-terry": ["french terry", "terry cloth"], "jersey-knit": ["jersey fabric", "jersey knit"],
                     "waffle-knit": ["waffle knit", "waffle fabric"]},
    "printing": {"dtg-print": ["direct to garment printing", "DTG printer"],
                 "embroidery": ["embroidered logo shirt", "machine embroidery"],
                 "heat-transfer": ["heat press", "heat transfer vinyl"], "no-logo": ["blank hoodie", "plain hoodie", "hoodie"]},
    "placement": {"front-left-chest": ["polo shirt logo", "embroidered chest logo"],
                  "centre-chest-or-full-front": ["printed hoodie", "hoodie print front"],
                  "back": ["back print hoodie", "jacket back print"], "sleeves": ["sleeve print", "sleeve patch"],
                  "hood": ["hood print", "hoodie hood"]},
    "hoodie_types": {"pullover": ["pullover hoodie", "hoodie"], "zip-up": ["zip hoodie", "zip-up hoodie", "hooded jacket zipper"],
                     "half-zip": ["half zip", "quarter zip pullover"]},
    "collars": {"hooded": ["hoodie", "hooded sweatshirt"], "double-layer-hood": ["hoodie hood", "lined hood"],
                "crew-neck": ["crewneck sweatshirt", "sweatshirt"], "mock-neck": ["mock neck", "turtleneck"],
                "funnel-neck": ["funnel neck", "turtleneck sweater"], "v-neck": ["v-neck sweater", "v-neck"]},
    "fit": {"regular": ["hoodie", "sweatshirt"], "loose-relaxed": ["loose sweatshirt", "relaxed fit"],
            "boxy": ["boxy t-shirt", "boxy fit"], "slim": ["slim fit shirt", "fitted shirt"]},
    "design_details": {"plain": ["plain sweatshirt", "blank sweatshirt"], "cut-out": ["cutout top", "cut-out dress"],
                       "distressed": ["distressed jeans", "ripped clothing"], "colour-block": ["color block jacket", "colour blocking"],
                       "patchwork": ["patchwork jacket", "patchwork clothing"], "raw-hem": ["raw hem", "frayed hem"],
                       "side-slits": ["side slit", "side vent shirt"]},
    "length": {"regular": ["sweatshirt", "hoodie"], "crop": ["crop top", "cropped sweater"], "longline": ["longline", "long hoodie"]},
    "sleeves": {"regular": ["set-in sleeve", "sweater"], "drop-shoulder": ["drop shoulder", "dropped shoulder"],
                "raglan": ["raglan sleeve"], "batwing": ["batwing sleeve", "dolman sleeve"]},
    "patterns": {"solid": ["solid color shirt", "plain t-shirt"], "colour-block": ["color block", "colour block"],
                 "striped": ["striped shirt", "breton stripe"], "graphic-or-letters": ["graphic t-shirt", "printed t-shirt"]},
    "packaging": {"individual-polybag": ["polybag", "plastic bag clothing", "t-shirt in plastic bag"],
                  "folded-with-tissue-paper": ["tissue paper", "gift wrap clothes"],
                  "on-a-hanger": ["clothes hanger", "coat hanger"], "branded-box": ["gift box", "clothing box"]},
    "gsm": {"160-200": ["thin cotton fabric", "voile"], "200-240": ["t-shirt fabric", "cotton jersey"],
            "320-400": ["fleece fabric", "polar fleece"]},
    "drawstrings": {"flat-cotton": ["drawstring hoodie", "drawstring"], "no-drawstrings": ["hoodie"]},
    "pockets": {"kangaroo-pocket": ["kangaroo pocket", "hoodie pocket"], "side-pockets": ["jacket pocket", "side pocket"],
                "no-pocket": ["crewneck sweatshirt", "sweatshirt"]},
    "labels": {"woven-neck-label": ["woven label", "clothing label"], "printed-neck-label": ["tagless label", "printed label"],
               "size-and-care-labels": ["care label", "laundry symbols label"], "hang-tag": ["hang tag", "price tag clothing"]},
}
COMMONS_PER_OPTION = 8


def commons() -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    found_path = WORK / "candidates.json"
    found = json.loads(found_path.read_text(encoding="utf-8")) if found_path.exists() else {}
    with httpx.Client(headers=HEADERS) as client:
        for topic, options in COMMONS_QUERIES.items():
            rows = []
            for key, queries in options.items():
                name = f"{topic}/{key}"
                if (OUT / f"{name}.webp").exists():
                    continue
                cands, seen = [], set()
                for query in queries:
                    if len(cands) >= COMMONS_PER_OPTION:
                        break
                    params = {"action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
                              "gsrsearch": f"{query} filetype:bitmap", "gsrlimit": 12, "prop": "imageinfo",
                              "iiprop": "url|extmetadata|size", "iiurlwidth": 900,
                              "iiextmetadatafilter": "Artist|LicenseShortName|LicenseUrl"}
                    r = client.get(COMMONS, params=params, timeout=60)
                    pages = sorted(r.json().get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 0))
                    for page in pages:
                        info = page["imageinfo"][0]
                        if page["title"] in seen or info.get("width", 0) < 500 or len(cands) >= COMMONS_PER_OPTION:
                            continue
                        seen.add(page["title"])
                        data = fetch(client, info.get("thumburl") or info["url"])
                        if not data:
                            continue
                        n = len(cands)
                        path = WORK / f"{topic}__{key}__{n}.jpg"
                        try:
                            Image.open(io.BytesIO(data)).convert("RGB").save(path, "JPEG", quality=85)
                        except Exception:
                            continue
                        meta = info.get("extmetadata", {})
                        artist = re.sub(r"<[^>]+>", "", meta.get("Artist", {}).get("value", "")).strip() or "Unknown"
                        cands.append({"n": n, "file": str(path), "title": page["title"], "creator": artist[:80],
                                      "licence": meta.get("LicenseShortName", {}).get("value", ""),
                                      "license_url": meta.get("LicenseUrl", {}).get("value"),
                                      "source": info.get("descriptionurl")})
                    time.sleep(0.5)
                found[name] = cands
                rows.append((name, cands))
                print(f"{name}: {len(cands)} candidates")
            if rows:
                sheet(topic, rows, columns=COMMONS_PER_OPTION, cell=170)
    found_path.write_text(json.dumps(found, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    unknown = ({f"{t}/{k}" for t, o in QUERIES.items() for k in o} | {f"{t}/{k}" for t, o in COMMONS_QUERIES.items() for k in o}) \
        - {f"{t}/{k}" for t, o in PROMPTS.items() for k in o}
    if unknown:
        sys.exit(f"queries for options with no photo slot: {sorted(unknown)}")
    if sys.argv[1:2] == ["search"]:
        search()
    elif sys.argv[1:2] == ["commons"]:
        commons()
    elif sys.argv[1:2] == ["pick"] and len(sys.argv) == 3:
        pick(sys.argv[2])
    else:
        sys.exit(__doc__)
