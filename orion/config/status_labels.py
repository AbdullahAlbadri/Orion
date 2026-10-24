"""Customer-facing names for order stages (tracker). Draft wording: TODO(decide) final English/Arabic copy."""

STATUS_LABELS: dict[str, dict[str, str]] = {
    "draft": {"en": "Describing your product", "ar": "وصف منتجك"},
    "pre_receipt_review": {"en": "Review your summary", "ar": "راجع ملخص طلبك"},
    "spec_frozen": {"en": "Summary confirmed", "ar": "تم تأكيد الملخص"},
    "sourcing": {"en": "Contacting manufacturers", "ar": "جارٍ التواصل مع المصانع"},
    "clarifying": {"en": "Confirming details with the manufacturer", "ar": "نؤكد التفاصيل مع المصنع"},
    "quote_received": {"en": "Preparing your quote", "ar": "نجهّز عرض السعر"},
}


def status_label(stage: str) -> dict[str, str]:
    return STATUS_LABELS.get(stage, {"en": "In progress", "ar": "قيد التنفيذ"})
