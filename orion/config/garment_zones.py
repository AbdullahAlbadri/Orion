"""The parts of each garment the customer can colour, drawn in the same 400 x 440 box as the placement editor
(web/lib/mockups.ts). The website draws these shapes from the question itself, so they live only here.

Each zone: id, English and Arabic name, a path per view (a zone without a back path has no back view), and
`stroke` for thin parts (tote handles) that are drawn as a thick line rather than a filled shape.
"""

from typing import Any, Optional

Zone = dict[str, Any]


def _zone(zone_id: str, en: str, ar: str, front: Optional[str], back: Optional[str] = "same", stroke: bool = False) -> Zone:
    return {"id": zone_id, "en": en, "ar": ar, "front": front, "back": front if back == "same" else back, "stroke": stroke}


def _mirror(path: str) -> str:
    """The same shape on the other side of the garment (x -> 400 - x) for paths of absolute M/L/Q/Z commands."""
    out, count = [], 0
    for token in path.replace(",", " ").split():
        if token[0] in "MLQZ":
            out.append(token[0])
            token = token[1:]
        if token:
            value = float(token)
            out.append(f"{400 - value:g}" if count % 2 == 0 else f"{value:g}")
            count += 1
    return " ".join(out)


_TEE_BODY = "M140 40 Q200 78 260 40 L302 140 L302 420 L98 420 L98 140 Z"
_TEE_BODY_BACK = "M140 40 Q200 56 260 40 L302 140 L302 420 L98 420 L98 140 Z"
_TEE_SLEEVE = "M140 40 L70 60 L12 150 L70 176 L98 140 Z"

_HOODIE_BODY = "M145 58 L255 58 L322 76 L302 170 L302 424 L98 424 L98 170 L78 76 Z"
_HOODIE_SLEEVE = "M145 58 L78 76 L12 300 L56 314 L98 170 Z"

_ABAYA_SLEEVE = "M100 54 L12 210 L50 226 L100 140 Z"

GARMENT_ZONES: dict[str, list[Zone]] = {
    "tee": [
        _zone("body", "Body", "الجسم", _TEE_BODY, _TEE_BODY_BACK),
        _zone("sleeves", "Sleeves", "الأكمام", _TEE_SLEEVE + " " + _mirror(_TEE_SLEEVE)),
        _zone("collar", "Neck rib", "ياقة الرقبة", "M140 40 Q200 78 260 40 L250 42 Q200 66 150 42 Z",
              "M140 40 Q200 56 260 40 L250 42 Q200 50 150 42 Z"),
    ],
    "polo": [
        _zone("body", "Body", "الجسم", _TEE_BODY, _TEE_BODY_BACK),
        _zone("sleeves", "Sleeves", "الأكمام", _TEE_SLEEVE + " " + _mirror(_TEE_SLEEVE)),
        _zone("collar", "Collar", "الياقة", "M140 40 Q200 78 260 40 L250 42 L218 92 L200 64 L182 92 L150 42 Z",
              "M140 40 Q200 56 260 40 L250 42 Q200 30 150 42 Z"),
    ],
    "hoodie": [
        _zone("body", "Body", "الجسم", _HOODIE_BODY),
        _zone("sleeves", "Sleeves", "الأكمام", _HOODIE_SLEEVE + " " + _mirror(_HOODIE_SLEEVE)),
        _zone("hood", "Hood", "القلنسوة", "M145 58 Q150 6 200 6 Q250 6 255 58 L232 62 Q200 92 168 62 Z",
              "M145 58 Q150 6 200 6 Q250 6 255 58 Q200 120 145 58 Z"),
        _zone("cuffs", "Cuffs and hem", "الأساور والحافة",
              "M12 300 L56 314 L61 290 L18 276 Z M388 300 L344 314 L339 290 L382 276 Z M98 396 L302 396 L302 424 L98 424 Z"),
        _zone("pocket", "Pocket", "الجيب", "M132 318 L268 318 L290 396 L110 396 Z", None),
    ],
    "abaya": [
        _zone("body", "Body", "الجسم",
              "M160 34 Q200 58 240 34 L300 54 L300 140 L332 432 L68 432 L100 140 L100 54 Z",
              "M160 34 Q200 46 240 34 L300 54 L300 140 L332 432 L68 432 L100 140 L100 54 Z"),
        _zone("sleeves", "Sleeves", "الأكمام", _ABAYA_SLEEVE + " " + _mirror(_ABAYA_SLEEVE)),
    ],
    "tote": [
        _zone("body", "Bag", "الحقيبة", "M88 150 L312 150 L322 424 L78 424 Z"),
        _zone("handles", "Handles", "المقابض", "M140 150 Q140 30 200 30 Q260 30 260 150", stroke=True),
    ],
}


def zones_for(mockup: Optional[str]) -> list[Zone]:
    return GARMENT_ZONES.get(mockup or "", [])
