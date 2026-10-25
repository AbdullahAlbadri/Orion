"""Size charts shown next to the size questions (the info button in the Quantity section).

Typical garment measurements for US/EU sizing, in cm, from common blank-garment charts; a guide for the
customer, not a promise. TODO(decide): replace each with the chart of the factory we work with.
"""

from typing import Any

_MEASURES = {
    "chest": {"en": "Chest width (laid flat)", "ar": "عرض الصدر (والقطعة مفرودة)"},
    "length": {"en": "Body length", "ar": "طول القطعة"},
    "sleeve": {"en": "Sleeve length", "ar": "طول الكم"},
    "abaya_length": {"en": "Abaya length", "ar": "طول العباية"},
}
_NOTE = {
    "en": "Approximate measurements for US/EU sizing. Asian sizing usually runs about one size smaller. "
          "The factory confirms its exact chart with the sample.",
    "ar": "قياسات تقريبية للمقاسات الأمريكية/الأوروبية. المقاسات الآسيوية أصغر بمقاس تقريبًا. "
          "يؤكد المصنع جدوله الدقيق مع العينة.",
}


def _chart(measures: list[str], sizes: dict[str, list[float]]) -> dict[str, Any]:
    return {"unit": "cm", "measures": [{"id": m, **_MEASURES[m]} for m in measures], "sizes": sizes, "note": _NOTE}


SIZE_CHARTS: dict[str, dict[str, Any]] = {
    "hoodie": _chart(["chest", "length", "sleeve"], {
        "S": [51, 68, 61], "M": [56, 71, 62], "L": [61, 74, 63], "XL": [66, 76, 64], "XXL": [71, 79, 65],
    }),
    "oversized_tee": _chart(["chest", "length", "sleeve"], {
        "S": [53, 70, 21], "M": [56, 72, 22], "L": [59, 74, 23], "XL": [62, 76, 24], "XXL": [65, 78, 25],
    }),
    "corporate_uniform": _chart(["chest", "length", "sleeve"], {
        "S": [48, 69, 20], "M": [51, 71, 21], "L": [54, 73, 22], "XL": [57, 75, 23], "XXL": [60, 77, 24],
    }),
    # Abaya sizes are the length in inches; the chart shows it in cm
    "abaya": _chart(["abaya_length"], {"52": [132], "54": [137], "56": [142], "58": [147], "60": [152]}),
}
