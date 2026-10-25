"""Make the photos for the guide pages, once. PAID: each photo is one image-model call (ask before running).

    uv run --with pillow python scripts/guide_images.py --dry-run              # list what would be made, no calls
    uv run --with pillow python scripts/guide_images.py --only materials/100-cotton fit/oversized
    uv run --with pillow python scripts/guide_images.py                        # everything still missing

A photo that already exists is never made again (delete the file to redo one). Photos are saved small (WebP,
800 px wide) in web/public/guides/<topic>/<slug>.webp, where the slug comes from the option's English name in
web/lib/guides.ts, the same way the page finds them (guideImage).
"""

import argparse
import asyncio
import io
import re
import sys
from pathlib import Path

from PIL import Image

from orion.config.settings import get_settings
from orion.tools.mockup import OpenRouterMockupMaker

ROOT = Path(__file__).resolve().parents[1]
GUIDES_TS = ROOT / "web" / "lib" / "guides.ts"
OUT = ROOT / "web" / "public" / "guides"

STYLE = ("Professional e-commerce studio product photo on a plain light warm-grey seamless background, soft even "
         "lighting, sharp focus, centred. No text, no words, no letters, no numbers, no watermark, no people, no hands.")
HOODIE = "a sand-beige hoodie"
EMBLEM = "a simple abstract emblem of three curved navy and gold stripes (no letters)"
MANNEQUIN = "on an invisible ghost mannequin"

# What each option's photo shows. Topics left out (timing, sizing, supply type...) are better explained in words.
PROMPTS: dict[str, dict[str, str]] = {
    "materials": {
        "100-cotton": "Macro close-up of a folded swatch of soft matte 100% cotton knit fabric with natural fibres, sand beige.",
        "cotton-polyester-80-20": "Macro close-up of a folded swatch of cotton-polyester fleece fabric, smooth face with a very slight sheen, sand beige.",
        "cotton-polyester-60-40": "Macro close-up of a folded swatch of tightly knit cotton-polyester fabric, smooth and crisp with a light sheen, sand beige.",
        "100-polyester": "Macro close-up of a folded swatch of smooth silky 100% polyester performance knit fabric with a subtle sheen, sand beige.",
        "organic-cotton": "Macro close-up of a folded swatch of undyed natural cream organic cotton knit fabric, with a small raw cotton boll beside it.",
        "recycled-polyester": "Macro close-up of a folded swatch of recycled polyester knit fabric with subtle melange flecks, sand beige.",
        "cotton-spandex": "Close-up of a sand-beige cotton-spandex knit fabric gently stretched between two clips, showing its elasticity.",
    },
    "fabric_types": {
        "knitted-fleece": f"Close-up of {HOODIE} turned partly inside out, showing the soft brushed fluffy fleece inside.",
        "french-terry": "Macro close-up of the back of sand-beige french terry fabric showing rows of small uncut loops.",
        "jersey-knit": "Macro close-up of fine smooth sand-beige jersey knit fabric showing tiny V-shaped knit stitches.",
        "waffle-knit": "Macro close-up of sand-beige waffle knit fabric with a raised square grid texture.",
        "woven": "Macro close-up of tightly woven sand-beige cotton twill fabric showing the diagonal criss-cross weave.",
    },
    "printing": {
        "screen-print": f"Close-up of the chest of {HOODIE} with {EMBLEM} screen printed: flat, bold, opaque ink with crisp edges.",
        "dtg-print": f"Close-up of the chest of {HOODIE} with a full-colour artwork with smooth colour gradients, printed with DTG ink soaked into the fabric.",
        "embroidery": f"Close-up of the chest of {HOODIE} with {EMBLEM} embroidered: raised satin stitches, visible thread texture.",
        "heat-transfer": f"Close-up of the chest of {HOODIE} with {EMBLEM} applied as glossy heat-transfer vinyl with slightly raised film edges.",
        "no-logo": f"A plain {HOODIE.split(' ', 1)[1]} without any print or logo, {MANNEQUIN}, front view.",
    },
    "placement": {
        "front-left-chest": f"{HOODIE.capitalize()} {MANNEQUIN}, front view, with a small {EMBLEM} on the wearer's left chest (right side of the photo).",
        "centre-chest-or-full-front": f"{HOODIE.capitalize()} {MANNEQUIN}, front view, with a large {EMBLEM} across the centre of the chest.",
        "back": f"{HOODIE.capitalize()} {MANNEQUIN}, back view, with a large {EMBLEM} across the upper back.",
        "sleeves": f"{HOODIE.capitalize()} {MANNEQUIN}, side view, with a small {EMBLEM} on the upper sleeve.",
        "hood": f"{HOODIE.capitalize()} {MANNEQUIN} with the hood up, three-quarter view, with a small {EMBLEM} on the side of the hood.",
    },
    "hoodie_types": {
        "pullover": f"A sand-beige pullover hoodie with a kangaroo pocket and no zip, {MANNEQUIN}, front view.",
        "zip-up": f"A sand-beige full zip-up hoodie with a metal zip from hem to neck, partly unzipped, {MANNEQUIN}, front view.",
        "half-zip": f"A sand-beige half-zip hoodie with a short zip from the neck to mid-chest, {MANNEQUIN}, front view.",
    },
    "collars": {
        "hooded": f"Close-up of the neckline of {HOODIE} with a classic single-layer hood lying flat, {MANNEQUIN}.",
        "double-layer-hood": f"Close-up of the neckline of {HOODIE} with a thick lined double-layer hood that keeps its shape, {MANNEQUIN}.",
        "crew-neck": f"Close-up of the neckline of a sand-beige crew neck sweatshirt with a ribbed round collar, {MANNEQUIN}.",
        "mock-neck": f"Close-up of the neckline of a sand-beige mock neck sweatshirt with a short raised ribbed collar, {MANNEQUIN}.",
        "funnel-neck": f"Close-up of the neckline of a sand-beige funnel neck sweatshirt with a tall collar cut from the body fabric, {MANNEQUIN}.",
        "v-neck": f"Close-up of the neckline of a sand-beige V-neck sweatshirt, {MANNEQUIN}.",
    },
    "fit": {
        "regular": f"A sand-beige pullover hoodie with a regular fit, {MANNEQUIN} of an average build, front view.",
        "loose-relaxed": f"A sand-beige pullover hoodie with a loose relaxed fit, slightly roomy, {MANNEQUIN}, front view.",
        "oversized": f"A sand-beige pullover hoodie with an oversized fit, dropped shoulders and long baggy sleeves, {MANNEQUIN}, front view.",
        "boxy": f"A sand-beige pullover hoodie with a boxy fit, wide, straight and slightly short, {MANNEQUIN}, front view.",
        "slim": f"A sand-beige pullover hoodie with a slim fit close to the body, {MANNEQUIN}, front view.",
    },
    "design_details": {
        "plain": f"A plain sand-beige pullover hoodie with no extra details, {MANNEQUIN}, front view.",
        "cut-out": f"A sand-beige pullover hoodie with stylish cut-out openings on the shoulders, {MANNEQUIN}, front view.",
        "distressed": f"A sand-beige pullover hoodie with a distressed look, frayed edges and small rips, {MANNEQUIN}, front view.",
        "colour-block": f"A pullover hoodie in colour block panels of sand beige, navy and white, {MANNEQUIN}, front view.",
        "patchwork": f"A pullover hoodie made of patchwork panels of different beige and brown fabrics, {MANNEQUIN}, front view.",
        "raw-hem": f"Close-up of the hem of {HOODIE} with a raw, unfolded cut edge.",
        "side-slits": f"Close-up of the lower side of {HOODIE} with a small side slit at the hem.",
    },
    "length": {
        "regular": f"A sand-beige pullover hoodie of regular length reaching the hips, {MANNEQUIN}, full front view.",
        "crop": f"A sand-beige cropped pullover hoodie ending above the waist, {MANNEQUIN}, full front view.",
        "longline": f"A sand-beige longline pullover hoodie reaching the upper thighs, {MANNEQUIN}, full front view.",
    },
    "sleeves": {
        "regular": f"A sand-beige pullover hoodie with regular set-in sleeves sewn at the shoulder edge, {MANNEQUIN}, front view.",
        "drop-shoulder": f"A sand-beige pullover hoodie with drop shoulders, the shoulder seam sitting low on the upper arm, {MANNEQUIN}, front view.",
        "raglan": f"A pullover hoodie with raglan sleeves in navy and a sand-beige body, diagonal seams from underarm to neck, {MANNEQUIN}, front view.",
        "batwing": f"A sand-beige pullover hoodie with batwing sleeves, very wide at the armpit and narrow at the wrist, {MANNEQUIN}, front view.",
    },
    "patterns": {
        "solid": f"A solid sand-beige pullover hoodie in one colour, {MANNEQUIN}, front view.",
        "colour-block": f"A pullover hoodie in bold colour block panels of sand beige, navy and burgundy, {MANNEQUIN}, front view.",
        "all-over-print": f"A pullover hoodie with an all-over abstract geometric print covering the whole garment, {MANNEQUIN}, front view.",
        "tie-dye": f"A pullover hoodie with a beige and blue tie-dye swirl pattern, {MANNEQUIN}, front view.",
        "camouflage": f"A pullover hoodie with a beige and brown desert camouflage pattern, {MANNEQUIN}, front view.",
        "striped": f"A pullover hoodie with horizontal sand-beige and navy stripes, {MANNEQUIN}, front view.",
        "graphic-or-letters": f"A sand-beige pullover hoodie with a large bold abstract graphic of shapes on the chest (no readable text), {MANNEQUIN}, front view.",
    },
    "packaging": {
        "individual-polybag": f"{HOODIE.capitalize()}, neatly folded inside a clear plastic polybag.",
        "folded-with-tissue-paper": f"{HOODIE.capitalize()}, neatly folded and wrapped in white tissue paper.",
        "on-a-hanger": f"{HOODIE.capitalize()} on a wooden hanger.",
        "branded-box": f"{HOODIE.capitalize()}, folded inside an open navy gift box with tissue paper, the closed lid beside it.",
    },
    "gsm": {
        "160-200": "Side view of a thin, light, slightly see-through folded sand-beige T-shirt fabric, showing its thinness.",
        "200-240": "Side view of a medium-thick folded sand-beige heavyweight T-shirt fabric, showing its thickness.",
        "280-320": "Side view of a folded medium-weight sand-beige hoodie fabric, showing its thickness.",
        "320-400": "Side view of a thick heavy folded sand-beige winter hoodie fleece fabric, showing its plush thickness.",
    },
    "drawstrings": {
        "flat-cotton": f"Close-up of the hood opening of {HOODIE} with flat cotton drawstrings.",
        "round-cord": f"Close-up of the hood opening of {HOODIE} with round cord drawstrings with metal tips.",
        "no-drawstrings": f"Close-up of the hood opening of {HOODIE} with no drawstrings, a clean hood edge.",
    },
    "pockets": {
        "kangaroo-pocket": f"Close-up of the front of {HOODIE} with a large kangaroo pocket.",
        "side-pockets": f"Close-up of the front of a sand-beige zip-up hoodie with two separate side pockets.",
        "no-pocket": f"Close-up of the front of {HOODIE} with no pocket, a clean front.",
    },
    "labels": {
        "woven-neck-label": f"Close-up inside the neck of {HOODIE} showing a woven fabric neck label with a simple emblem (no readable text).",
        "printed-neck-label": f"Close-up inside the neck of {HOODIE} showing a label printed directly on the fabric with a simple emblem (no readable text).",
        "size-and-care-labels": f"Close-up of small white satin size and care labels sewn into the side seam of {HOODIE}, with care symbols only.",
        "hang-tag": f"{HOODIE.capitalize()} folded, with a kraft paper hang tag on a string showing only a simple emblem.",
    },
}


def slug(name: str) -> str:
    return re.sub(r"^-+|-+$", "", re.sub(r"[^a-z0-9]+", "-", name.lower()))


def guide_items() -> dict[str, list[str]]:
    """{topic: [option slugs]} read from web/lib/guides.ts, the page's own source."""
    text = GUIDES_TS.read_text(encoding="utf-8")
    body = text[text.index("export const GUIDES"):text.index("export const QUESTION_GUIDES")]
    items: dict[str, list[str]] = {}
    topic = None
    for line in body.splitlines():
        if m := re.match(r"^  (\w+): \{", line):
            topic = m.group(1)
            items[topic] = []
        elif topic and (m := re.search(r'\{ name: t\("[^"]*", "([^"]+)"\)', line)):
            items[topic].append(slug(m.group(1)))
    return items


def save_webp(data: bytes, path: Path) -> int:
    image = Image.open(io.BytesIO(data)).convert("RGB")
    if image.width > 800:
        image = image.resize((800, round(image.height * 800 / image.width)), Image.LANCZOS)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "WEBP", quality=80)
    return path.stat().st_size


async def main() -> int:
    parser = argparse.ArgumentParser(prog="guide_images")
    parser.add_argument("--only", nargs="*", help="topic/slug pairs to make (default: everything missing)")
    parser.add_argument("--dry-run", action="store_true", help="list what would be made; no calls")
    parser.add_argument("--budget", type=float, default=5.0, help="stop once this many USD are spent")
    parser.add_argument("--model", help="image model (default: MOCKUP_MODEL)")
    args = parser.parse_args()

    items = guide_items()
    wanted = []
    for topic, prompts in PROMPTS.items():
        for key in prompts:
            if key not in items.get(topic, []):
                print(f"! {topic}/{key} has a prompt but no option on the page", file=sys.stderr)
                return 1
            wanted.append(f"{topic}/{key}")
    if args.only:
        unknown = set(args.only) - set(wanted)
        if unknown:
            print(f"! unknown: {sorted(unknown)}", file=sys.stderr)
            return 1
        wanted = [w for w in wanted if w in args.only]
    todo = [w for w in wanted if not (OUT / f"{w}.webp").exists()]   # made once: existing photos are kept
    print(f"{len(wanted)} photos wanted, {len(wanted) - len(todo)} already made, {len(todo)} to make")
    if args.dry_run:
        print("\n".join(todo))
        return 0

    settings = get_settings()
    maker = OpenRouterMockupMaker(settings.openrouter_api_key.get_secret_value(), settings.openrouter_base_url,
                                  args.model or settings.mockup_model)
    spent = 0.0
    for name in todo:
        if spent >= args.budget:
            print(f"budget of ${args.budget} reached; stopping")
            break
        topic, key = name.split("/")
        try:
            image = await maker.make(f"{PROMPTS[topic][key]} {STYLE}", [], "4:3")
        except Exception as e:
            print(f"x {name}: {e}")
            continue
        size = save_webp(image.data, OUT / f"{name}.webp")
        spent += image.cost or 0
        print(f"+ {name}  {size // 1024} KB  ${image.cost if image.cost is not None else '?'}  (total ${spent:.3f})")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
