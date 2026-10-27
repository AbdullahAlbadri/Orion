"""AI mockups: a photo-like picture of the product the customer is ordering, made by an image model.

The prompt is written in code from the form answers (never by an LLM), and the customer's logo goes in as a
reference image. A mockup is only an illustration to help the customer imagine the product: the frozen spec is
what gets made, and mockups are never sent to a factory.
"""

import base64
import logging
import io
from dataclasses import dataclass
from typing import Any, Optional, Protocol

import httpx
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageStat

from orion.tools.brief import mockup_brief
from orion.tools.placement_diagram import GARMENTS, VIEW_H, VIEW_W, parse_path
from orion.spec import (
    QUANTITY_ID, SIZE_TABLE_ID, Question, format_answer, is_file_list, is_placement_list,
)

log = logging.getLogger("orion.mockup")

# Raster formats image models accept as a reference (SVG, PDF and EPS logos can't be shown)
REFERENCE_TYPES = {"image/png", "image/jpeg", "image/webp"}
# Answers that don't change how the product looks
NOT_VISUAL = {QUANTITY_ID, SIZE_TABLE_ID, "size_standard", "needed_by", "sample", "packaging", "labels", "fit_reference"}


@dataclass
class MockupImage:
    data: bytes
    content_type: str
    cost: Optional[float] = None       # USD, when the provider reports it


class MockupMaker(Protocol):
    model: str

    async def make(self, prompt: str, references: list[tuple[bytes, str]], aspect_ratio: str,
                   model: Optional[str] = None) -> MockupImage: ...


def mockup_prompt(product: str, questions: list[Question], answers: dict[str, Any]) -> tuple[str, str]:
    """(prompt, aspect ratio) for the BLANK product: the order brief (Markdown) in full. The customer's own pictures
    are never given to the image model (it redraws them); `compose_artwork` puts the real files on afterwards."""
    brief, back = mockup_brief(product, questions, answers)
    return brief, ("16:9" if back else "1:1")


def _garment_box(image: Image.Image, left: int, right: int) -> Optional[tuple[int, int, int, int]]:
    """Where the garment is in one view of the photo: everything that differs from the (white) background."""
    view = image.convert("RGB").crop((left, 0, right, image.height))
    corners = [view.getpixel(c) for c in
               ((2, 2), (view.width - 3, 2), (2, view.height - 3), (view.width - 3, view.height - 3))]
    bg = tuple(sorted(c[i] for c in corners)[1] for i in range(3))            # the middle value of the corners
    diff = ImageChops.difference(view, Image.new("RGB", view.size, bg)).convert("L").point(lambda v: 255 if v > 28 else 0)
    cols, rows = diff.resize((view.width, 1), Image.BOX), diff.resize((1, view.height), Image.BOX)
    xs = [i for i in range(view.width) if cols.getpixel((i, 0)) > 6]
    ys = [i for i in range(view.height) if rows.getpixel((0, i)) > 6]
    if not xs or not ys or xs[-1] - xs[0] < view.width * 0.2:
        return None
    return left + xs[0], ys[0], left + xs[-1], ys[-1]


def target_boxes(base: bytes, mockup: Optional[str], placements: list[dict]) -> list[tuple[dict, tuple[int, int, int, int]]]:
    """Where each placement lands in the blank photo, in pixels: (placement, (left, top, right, bottom)). The garment is
    found in the photo and the placement editor's drawing is stretched over it."""
    image = Image.open(io.BytesIO(base)).convert("RGB")
    cm_per_unit, views = GARMENTS.get(mockup or "", GARMENTS["tee"])
    two = any(p.get("view") == "back" for p in placements)
    halves = {"front": (0, image.width // 2 if two else image.width), "back": (image.width // 2, image.width)}
    out = []
    for view, (left, right) in halves.items():
        mine = [p for p in placements if p.get("view") == view]
        if not mine:
            continue
        box = _garment_box(image, left, right) or (
            left + int((right - left) * 0.08), int(image.height * 0.05), right - int((right - left) * 0.08),
            int(image.height * 0.95))
        points = [pt for path in (views[view][0], *views[view][1]) for line in parse_path(path) for pt in line]
        gx0, gx1 = min(x for x, _ in points), max(x for x, _ in points)
        gy0, gy1 = min(y for _, y in points), max(y for _, y in points)
        sx, sy = (box[2] - box[0]) / (gx1 - gx0), (box[3] - box[1]) / (gy1 - gy0)
        for p in mine:
            w, h = p["width_cm"] / cm_per_unit * sx, p["height_cm"] / cm_per_unit * sy
            cx = box[0] + (p["x"] * VIEW_W - gx0) * sx
            cy = box[1] + (p["y"] * VIEW_H - gy0) * sy
            out.append((p, (int(cx - w / 2), int(cy - h / 2), int(cx + w / 2), int(cy + h / 2))))
    return out


def artwork_guide(base: bytes, boxes: list[tuple[dict, tuple[int, int, int, int]]]) -> bytes:
    """The blank photo with a numbered magenta box where each artwork goes, shown to the editing model."""
    image = Image.open(io.BytesIO(base)).convert("RGB")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(max(18, image.height // 30))
    for n, (_, box) in enumerate(boxes, 1):
        draw.rectangle(box, outline=(255, 0, 200), width=max(3, image.height // 300))
        draw.text((box[0] + 8, box[1] + 6), str(n), font=font, fill=(255, 0, 200))
    out = io.BytesIO()
    image.save(out, "PNG")
    return out.getvalue()


def artwork_prompt(boxes: list[tuple[dict, tuple[int, int, int, int]]], logo_numbers: list[int], method: str = "") -> str:
    """The editing instruction (Markdown). `logo_numbers[i]` is the attached image number of box i's artwork."""
    lines = ["# Edit task: put the customer's artwork on the product", "",
             "## Images",
             "- Image 1: the blank product photo. Keep it exactly: the same garment, shape, colour, pose, lighting "
             "and background.",
             "- Image 2: the same photo with numbered magenta boxes marking where each artwork goes.",
             "- Images 3 and after: the customer's real artwork files.", "", "## Placements"]
    for n, ((p, _), image_no) in enumerate(zip(boxes, logo_numbers), 1):
        kind = "logo" if p.get("kind") == "logo" else "label"
        lines.append(f"- Box {n} ({p['view']} view, {p['width_cm']:g} x {p['height_cm']:g} cm {kind}): artwork = image {image_no}")
    lines += ["", "## Rules",
              "- Put each artwork inside its box, centred, scaled to fit the box while keeping its own proportions.",
              "- Copy every artwork exactly: the same shapes, colours, letters and proportions. Never redraw, restyle, "
              "translate, crop or invent anything. A photograph stays a photograph.",
              f"- Make it look really {method or 'printed'} on the fabric: it follows the folds and the texture, "
              "with natural shading, and it stays clear of zippers and seams where it can.",
              "- Remove the magenta boxes and numbers completely: they are not part of the product.",
              "- Do not add anything else: no other logos, text or changes to the garment or the background."]
    return "\n".join(lines) + "\n"


def compose_artwork(base: bytes, mockup: Optional[str], placements: list[dict], pictures: dict[str, bytes]) -> bytes:
    """The customer's real files on the blank product photo, at the placed positions and sizes. The exact pictures,
    never redrawn: the position comes from where the garment is in the photo, mapped from the placement editor's
    drawing. Returns PNG bytes."""
    image = Image.open(io.BytesIO(base)).convert("RGB")
    cm_per_unit, views = GARMENTS.get(mockup or "", GARMENTS["tee"])
    two = any(p.get("view") == "back" for p in placements)
    halves = {"front": (0, image.width // 2 if two else image.width), "back": (image.width // 2, image.width)}
    for view, (left, right) in halves.items():
        mine = [p for p in placements if p.get("view") == view and p.get("file_id") in pictures]
        if not mine:
            continue
        box = _garment_box(image, left, right)
        if box is None:                                   # no garment found: assume it fills most of the view
            box = (left + int((right - left) * 0.08), int(image.height * 0.05), right - int((right - left) * 0.08),
                   int(image.height * 0.95))
        points = [pt for path in (views[view][0], *views[view][1]) for line in parse_path(path) for pt in line]   # hood included
        gx0, gx1 = min(x for x, _ in points), max(x for x, _ in points)
        gy0, gy1 = min(y for _, y in points), max(y for _, y in points)
        sx, sy = (box[2] - box[0]) / (gx1 - gx0), (box[3] - box[1]) / (gy1 - gy0)
        for p in mine:
            try:
                art = Image.open(io.BytesIO(pictures[p["file_id"]])).convert("RGBA")
            except Exception:
                continue
            w = max(4, int(p["width_cm"] / cm_per_unit * sx))
            h = max(4, int(p["height_cm"] / cm_per_unit * sy))
            art.thumbnail((w, h))
            cx = box[0] + (p["x"] * VIEW_W - gx0) * sx
            cy = box[1] + (p["y"] * VIEW_H - gy0) * sy
            pos = (int(cx - art.width / 2), int(cy - art.height / 2))
            # fabric folds and shading show through a little, so it reads as printed rather than pasted
            crop = image.crop((pos[0], pos[1], pos[0] + art.width, pos[1] + art.height)).convert("L")
            mean = max(1, ImageStat.Stat(crop).mean[0])
            shade = crop.point(lambda v, m=mean: min(255, int(v * 255 / m))).convert("RGB")
            flat = art.convert("RGB")
            image.paste(Image.blend(flat, ImageChops.multiply(flat, shade), 0.3), pos, art.getchannel("A"))
    out = io.BytesIO()
    image.save(out, "PNG")
    return out.getvalue()


class OpenRouterMockupMaker:
    """OpenRouter's image endpoint (POST /images) with the logo as an input reference."""

    def __init__(self, api_key: str, base_url: str, model: str, fallback_model: str = ""):
        self._key, self._url, self.model = api_key, base_url.rstrip("/") + "/images", model
        self._fallback = fallback_model

    async def make(self, prompt: str, references: list[tuple[bytes, str]], aspect_ratio: str,
                   model: Optional[str] = None) -> MockupImage:
        """`model`: use this one only (the editing pass); otherwise the main model, then the fallback."""
        if model:
            return await self._make(model, prompt, references, aspect_ratio)
        try:
            return await self._make(self.model, prompt, references, aspect_ratio)
        except Exception:
            if not self._fallback or self._fallback == self.model:
                raise
            log.exception("mockup model %s failed; trying %s", self.model, self._fallback)
            return await self._make(self._fallback, prompt, references, aspect_ratio)

    async def _make(self, model: str, prompt: str, references: list[tuple[bytes, str]], aspect_ratio: str) -> MockupImage:
        body: dict[str, Any] = {"model": model, "prompt": prompt, "aspect_ratio": aspect_ratio}
        if references:
            body["input_references"] = [
                {"type": "image_url",
                 "image_url": {"url": f"data:{ctype};base64,{base64.b64encode(data).decode()}"}}
                for data, ctype in references
            ]
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(self._url, json=body, headers={"Authorization": f"Bearer {self._key}"})
        r.raise_for_status()
        payload = r.json()
        image = payload["data"][0]
        cost = (payload.get("usage") or {}).get("cost")
        return MockupImage(base64.b64decode(image["b64_json"]), image.get("media_type") or "image/png",
                           float(cost) if cost is not None else None)
