"""Colour helpers: HEX validation and a plain colour name, so a factory or an image model reads "navy (#1b2a4a)"
instead of a bare code."""

import re

HEX = re.compile(r"^#[0-9a-fA-F]{6}$")

_NAMES = {
    "black": (20, 20, 22), "white": (245, 245, 245), "grey": (128, 128, 128), "light grey": (200, 200, 200),
    "charcoal": (60, 60, 64), "navy": (24, 38, 78), "blue": (30, 90, 200), "light blue": (140, 190, 235),
    "teal": (20, 130, 130), "green": (40, 140, 70), "olive": (110, 110, 50), "khaki": (170, 160, 110),
    "beige": (225, 210, 180), "cream": (245, 235, 210), "brown": (110, 70, 40), "tan": (190, 140, 90),
    "red": (200, 30, 40), "burgundy": (110, 20, 40), "pink": (240, 150, 180), "orange": (240, 130, 30),
    "yellow": (245, 205, 40), "gold": (200, 160, 60), "purple": (110, 50, 150), "lavender": (190, 170, 230),
}


def color_name(hex_code: str) -> str:
    """The nearest plain name for a HEX colour."""
    h = hex_code.lstrip("#")
    rgb = tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    return min(_NAMES, key=lambda n: sum((a - b) ** 2 for a, b in zip(rgb, _NAMES[n])))
