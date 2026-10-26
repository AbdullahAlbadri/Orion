"""AI mockups: a photo-like picture of the product the customer is ordering, made by an image model.

The prompt is written in code from the form answers (never by an LLM), and the customer's logo goes in as a
reference image. A mockup is only an illustration to help the customer imagine the product: the frozen spec is
what gets made, and mockups are never sent to a factory.
"""

import base64
from dataclasses import dataclass
from typing import Any, Optional, Protocol

import httpx

from orion.spec import (
    QUANTITY_ID, SIZE_TABLE_ID, Question, describe_placement, format_answer, is_file_list, is_placement_list,
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


def mockup_prompt(product: str, questions: list[Question], answers: dict[str, Any],
                  pictures: list[str], uploads: Optional[dict[str, str]] = None) -> tuple[str, str]:
    """(prompt, aspect ratio) from the form as it is now. `pictures`: the file ids of the reference images sent
    with the prompt, in order (image 1, image 2...). `uploads`: file id -> the form question it was uploaded for,
    for pictures that are not placed on the product (a sticker, a label design)."""
    has_logo = bool(pictures)
    details, placements = [], []
    for q in questions:
        value = answers.get(q.id)
        if q.id in NOT_VISUAL or value in (None, "", []) or is_file_list(value) or q.type == "file":
            continue
        if is_placement_list(value):
            placements = value
            continue
        if q.type == "placement":                       # typed as text instead of drawn
            details.append(f"- Logo position: {format_answer(value)[:200]}")
            continue
        details.append(f"- {q.prompt.rstrip('?؟:. ')}: {format_answer(value)[:200]}")

    back = any(p.get("view") == "back" for p in placements)
    lines = [f"Photorealistic e-commerce product photo of a custom {product}, for a brand mockup.", "",
             "Product details:", *details]
    placed_ids = {p.get("file_id") for p in placements}
    loose = [(i + 1, (uploads or {}).get(fid, "")) for i, fid in enumerate(pictures) if fid not in placed_ids]
    if placements and has_logo:
        def which(p: dict) -> str:
            if p.get("file_id") in pictures:
                return f" - attached image {pictures.index(p['file_id']) + 1}"
            return " - attached image 1" if len(pictures) == 1 and p.get("kind") == "logo" else ""
        lines += ["", "Logo and label positions (left and right are the wearer's; the wearer's left is the right side "
                      "of a front-facing photo):", *[f"- {describe_placement(p)}{which(p)}" for p in placements]]
    elif has_logo:
        lines += ["", "Put the attached logo on the left chest, small."]
    if has_logo:
        if loose and placements:
            lines += ["", "Other attached artwork (also show it, on the product where it fits naturally):",
                      *[f"- attached image {n}" + (f" ({q})" if q else "") for n, q in loose]]
        lines += ["", f"The {len(pictures)} attached image(s) are the customer's real artwork. Copy each one exactly: "
                      "the same shapes, colours, letters and proportions, never redrawn, restyled, translated or "
                      "invented. Show each artwork once, at its stated position and size, applied with the "
                      "decoration method above. Do not add any other logos, text, labels or watermarks."]
    else:
        lines += ["", "No logo: show the product without any logo, text or print."]
    lines += ["", ("Show the front and back views side by side" if back else "Show the front view")
              + ", on an invisible mannequin, on a plain light grey studio background with soft even lighting. "
                "No people, no hands, no extra props."]
    return "\n".join(lines), ("16:9" if back else "1:1")


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
