"""AI mockups: a photo-like picture of the product the customer is ordering, made by an image model.

The prompt is written in code from the form answers (never by an LLM), and the customer's logo goes in as a
reference image. A mockup is only an illustration to help the customer imagine the product: the frozen spec is
what gets made, and mockups are never sent to a factory.
"""

import base64
import io
from dataclasses import dataclass
from typing import Any, Optional, Protocol

import httpx
from PIL import Image, ImageChops, ImageStat

from orion.tools.placement_diagram import GARMENTS, VIEW_H, VIEW_W, parse_path
from orion.spec import (
    QUANTITY_ID, SIZE_TABLE_ID, Question, format_answer, is_file_list, is_placement_list,
)

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

    async def make(self, prompt: str, references: list[tuple[bytes, str]], aspect_ratio: str) -> MockupImage: ...


def mockup_prompt(product: str, questions: list[Question], answers: dict[str, Any]) -> tuple[str, str]:
    """(prompt, aspect ratio) for the BLANK product: the customer's own pictures are never given to the image model
    (it redraws them); `compose_artwork` puts the real files on the photo afterwards."""
    details, placements = [], []
    for q in questions:
        value = answers.get(q.id)
        if q.id in NOT_VISUAL or value in (None, "", []) or is_file_list(value) or q.type == "file":
            continue
        if is_placement_list(value):
            placements = value
            continue
        if q.type == "placement":
            continue
        details.append(f"- {q.prompt.rstrip('?؟:. ')}: {format_answer(value)[:200]}")

    back = any(p.get("view") == "back" for p in placements)
    lines = [f"Photorealistic e-commerce product photo of a plain, blank custom {product}, for a brand mockup.", "",
             "Product details:", *details, "",
             "The garment is completely blank: no logo, no print, no embroidery, no text, no label, no pattern "
             "or graphic of any kind on the fabric. (Any logos are added afterwards.)",
             "", ("Show the front and back views side by side, each facing the camera straight on and centred in its "
                  "half of the picture" if back else "Show the front view, facing the camera straight on and centred")
             + ", on an invisible mannequin, on a seamless pure white studio background with soft even lighting. "
               "No people, no hands, no extra props."]
    return "\n".join(lines), ("16:9" if back else "1:1")


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

    def __init__(self, api_key: str, base_url: str, model: str):
        self._key, self._url, self.model = api_key, base_url.rstrip("/") + "/images", model

    async def make(self, prompt: str, references: list[tuple[bytes, str]], aspect_ratio: str) -> MockupImage:
        body: dict[str, Any] = {"model": self.model, "prompt": prompt, "aspect_ratio": aspect_ratio}
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
