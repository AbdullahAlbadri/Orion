"""The placement drawing sent to the manufacturer: the flat garment (front and back) with every logo and label
drawn where the customer placed it, numbered, with its size in centimetres. Same drawings and coordinates as the
website's placement editor (web/lib/mockups.ts), made in code from the frozen spec, never from chat.
"""

import io
import re
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

VIEW_W, VIEW_H = 400, 440

_HOODIE_BODY = "M145 58 L255 58 L322 76 L388 300 L344 314 L302 170 L302 424 L98 424 L98 170 L56 314 L12 300 L78 76 Z"
_TEE_FRONT = "M140 40 Q200 78 260 40 L330 60 L388 150 L330 176 L302 140 L302 420 L98 420 L98 140 L70 176 L12 150 L70 60 Z"
_TEE_BACK = "M140 40 Q200 56 260 40 L330 60 L388 150 L330 176 L302 140 L302 420 L98 420 L98 140 L70 176 L12 150 L70 60 Z"
_ABAYA = "M160 34 Q200 {q} 240 34 L300 54 L388 210 L350 226 L300 140 L332 432 L68 432 L100 140 L50 226 L12 210 L100 54 Z"
_TOTE = "M88 150 L312 150 L322 424 L78 424 Z"
_TOTE_HANDLE = "M140 150 Q140 30 200 30 Q260 30 260 150"

# mockup key -> (centimetres per drawing unit on a size M, {view: (body, [detail paths])})
GARMENTS: dict[str, tuple[float, dict[str, tuple[str, list[str]]]]] = {
    "tee": (0.27, {"front": (_TEE_FRONT, ["M150 42 Q200 66 250 42"]), "back": (_TEE_BACK, [])}),
    "polo": (0.27, {
        "front": (_TEE_FRONT, ["M150 42 L182 92 L200 64 L218 92 L250 42", "M200 64 L200 140"]),
        "back": (_TEE_BACK, ["M150 40 Q200 30 250 40"]),
    }),
    "hoodie": (0.29, {
        "front": (_HOODIE_BODY, ["M145 60 Q150 6 200 6 Q250 6 255 60", "M168 62 Q200 92 232 62",
                                 "M186 80 L182 128 M214 80 L218 128", "M132 318 L268 318 L290 396 L110 396 Z"]),
        "back": (_HOODIE_BODY, ["M145 60 Q150 6 200 6 Q250 6 255 60", "M150 60 Q200 120 250 60"]),
    }),
    "abaya": (0.3, {
        "front": (_ABAYA.format(q=58), ["M200 52 L200 432"]),
        "back": (_ABAYA.format(q=46), []),
    }),
    "tote": (0.173, {"front": (_TOTE, [_TOTE_HANDLE]), "back": (_TOTE, [_TOTE_HANDLE])}),
}

_TOKEN = re.compile(r"[MLQZhH]|-?\d+(?:\.\d+)?")


def parse_path(d: str, steps: int = 12) -> list[list[tuple[float, float]]]:
    """A path of M, L, Q, H, h and Z commands as polylines (a curve becomes `steps` short lines)."""
    tokens = _TOKEN.findall(d)
    lines: list[list[tuple[float, float]]] = []
    current: list[tuple[float, float]] = []
    pos = (0.0, 0.0)
    i, cmd = 0, ""
    num = lambda: float(tokens[i])    # noqa: E731
    while i < len(tokens):
        if tokens[i] in "MLQZhH":
            cmd = tokens[i]
            i += 1
            if cmd == "Z":
                if current:
                    current.append(current[0])
                    lines.append(current)
                    current = []
                continue
        if cmd == "M":
            if current:
                lines.append(current)
            pos = (num(), float(tokens[i + 1]))
            current, i, cmd = [pos], i + 2, "L"
        elif cmd == "L":
            pos = (num(), float(tokens[i + 1]))
            current.append(pos)
            i += 2
        elif cmd == "Q":
            cx, cy, x, y = (float(t) for t in tokens[i:i + 4])
            x0, y0 = pos
            for s in range(1, steps + 1):
                t = s / steps
                current.append(((1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t * t * x,
                                (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t * t * y))
            pos = (x, y)
            i += 4
        elif cmd in "hH":
            x = num() + (pos[0] if cmd == "h" else 0)
            pos = (x, pos[1])
            current.append(pos)
            i += 1
        else:
            i += 1
    if current:
        lines.append(current)
    return lines


def _font(size: int):
    try:
        return ImageFont.load_default(size)
    except TypeError:                 # very old Pillow: fixed-size font
        return ImageFont.load_default()


def render(mockup: Optional[str], placements: list[dict], pictures: dict[str, bytes]) -> Optional[bytes]:
    """A PNG of the placements, or None when there is nothing to draw. `pictures`: file id -> image bytes."""
    placements = [p for p in placements if p.get("view") in ("front", "back")]
    if not placements:
        return None
    cm_per_unit, views = GARMENTS.get(mockup or "", GARMENTS["tee"])
    shown = [v for v in ("front", "back") if any(p["view"] == v for p in placements)]
    scale, pad, head = 1.5, 30, 54
    w, h = int(VIEW_W * scale), int(VIEW_H * scale)
    legend_h = 34 * len(placements) + 24
    canvas = Image.new("RGB", (pad + len(shown) * (w + pad), head + h + pad + legend_h), "white")
    draw = ImageDraw.Draw(canvas)
    small, big = _font(18), _font(26)
    ink, grey, gold = (40, 40, 46), (150, 150, 158), (190, 140, 40)

    number = {id(p): n for n, p in enumerate(placements, 1)}
    for col, view in enumerate(shown):
        ox, oy = pad + col * (w + pad), head
        draw.text((ox, 14), view.upper(), font=big, fill=ink)
        body, details = views[view]
        for path in [body, *details]:
            for line in parse_path(path):
                draw.line([(ox + x * scale, oy + y * scale) for x, y in line], fill=grey if path != body else ink,
                          width=3 if path == body else 2, joint="curve")
        for p in (p for p in placements if p["view"] == view):
            pw, ph = p["width_cm"] / cm_per_unit * scale, p["height_cm"] / cm_per_unit * scale
            cx, cy = ox + p["x"] * w, oy + p["y"] * h
            box = (cx - pw / 2, cy - ph / 2, cx + pw / 2, cy + ph / 2)
            data = pictures.get(p.get("file_id") or "")
            if data:
                try:
                    pic = Image.open(io.BytesIO(data)).convert("RGBA")
                    pic.thumbnail((max(1, int(pw)), max(1, int(ph))))
                    canvas.paste(pic, (int(cx - pic.width / 2), int(cy - pic.height / 2)), pic)
                except Exception:      # an unreadable picture: the numbered box still shows where it goes
                    pass
            draw.rectangle(box, outline=gold, width=2)
            n = str(number[id(p)])
            draw.ellipse((box[0] - 12, box[1] - 12, box[0] + 12, box[1] + 12), fill=gold)
            draw.text((box[0], box[1]), n, font=small, fill="white", anchor="mm")

    y = head + h + pad
    draw.line([(pad, y - 12), (canvas.width - pad, y - 12)], fill=grey, width=1)
    for p in placements:
        kind = "Logo" if p.get("kind") == "logo" else "Label"
        text = f"{number[id(p)]}.  {kind}, {p['view']}, {p['width_cm']:g} x {p['height_cm']:g} cm"
        draw.text((pad, y), text, font=small, fill=ink)
        y += 34
    out = io.BytesIO()
    canvas.save(out, "PNG")
    return out.getvalue()
