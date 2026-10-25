"""Customer-facing names for order stages, who each stage waits on, and the updates customers get.

Draft wording: TODO(decide) final English/Arabic copy (docs/website/04-order-page.md timeline).
Never promise a date or a duration here.
"""

from typing import Optional

STATUS_LABELS: dict[str, dict[str, str]] = {
    "draft": {"en": "Describing your product", "ar": "وصف منتجك"},
    "pre_receipt_review": {"en": "Review your summary", "ar": "راجع ملخص طلبك"},
    "spec_frozen": {"en": "Summary confirmed", "ar": "تم تأكيد الملخص"},
    "sourcing": {"en": "Contacting manufacturers", "ar": "جارٍ التواصل مع المصانع"},
    "clarifying": {"en": "Confirming details with the manufacturer", "ar": "نؤكد التفاصيل مع المصنع"},
    "quote_received": {"en": "Preparing your quote", "ar": "نجهّز عرض السعر"},
    "quote_review": {"en": "Your quote is ready", "ar": "عرض السعر جاهز"},
    "awaiting_payment": {"en": "Waiting for payment", "ar": "بانتظار الدفع"},
    "sample_requested": {"en": "Your sample is being made", "ar": "يجري تجهيز عينتك"},
    "sample_in_transit": {"en": "Your sample is on its way", "ar": "عينتك في الطريق"},
    "sample_review": {"en": "Review your sample", "ar": "راجع عينتك"},
    "in_production": {"en": "In production", "ar": "قيد التصنيع"},
    "quality_check": {"en": "Quality check", "ar": "فحص الجودة"},
    "shipped": {"en": "On its way", "ar": "في الطريق"},
    "in_transit": {"en": "On its way", "ar": "في الطريق"},
    "customs_paperwork": {"en": "Customs paperwork", "ar": "أوراق الجمارك"},
    "delivered": {"en": "Delivered", "ar": "تم التسليم"},
    "completed": {"en": "Delivered", "ar": "تم التسليم"},
    "cancelled": {"en": "Cancelled", "ar": "ملغى"},
    "expired": {"en": "Expired", "ar": "منتهي"},
    "refunded": {"en": "Refunded", "ar": "مسترد"},
}

# Who the order waits on in each stage (stats: "waiting on you vs waiting on the factory")
STAGE_OWNER: dict[str, Optional[str]] = {
    "draft": "customer",
    "pre_receipt_review": "customer",
    "spec_frozen": "orion",
    "sourcing": "factory",
    "clarifying": "factory",
    "quote_received": "orion",
    "quote_review": "customer",
    "awaiting_payment": "customer",
    "sample_requested": "factory",
    "sample_in_transit": "shipping",
    "sample_review": "customer",
    "in_production": "factory",
    "quality_check": "orion",
    "shipped": "shipping",
    "in_transit": "shipping",
    "customs_paperwork": "orion",
    "delivered": None,
    "completed": None,
    "cancelled": None,
    "expired": None,
    "refunded": None,
}

# Phases for "time per stage" on the stats page
STAGE_PHASE: dict[str, str] = {
    "draft": "specification", "pre_receipt_review": "specification",
    "spec_frozen": "quote", "sourcing": "quote", "clarifying": "quote", "quote_received": "quote",
    "quote_review": "payment", "awaiting_payment": "payment",
    "sample_requested": "sample", "sample_in_transit": "sample", "sample_review": "sample",
    "in_production": "production", "quality_check": "production",
    "shipped": "shipping", "in_transit": "shipping",
    "customs_paperwork": "customs",
}
PHASES = ["specification", "quote", "payment", "sample", "production", "shipping", "customs"]
CLOSED = {"delivered", "completed", "cancelled", "expired", "refunded"}

# Stages that mean the customer confirmed the summary (the product is saved from here on)
UNSUBMITTED = {"draft", "pre_receipt_review", "cancelled"}

# Updates sent to the customer when an order enters a stage. Stages the customer moved
# the order into themselves (draft, summary, confirm, discard) send nothing.
STAGE_UPDATES: dict[str, dict[str, str]] = {
    "sourcing": {
        "title_en": "We sent your order to manufacturers", "title_ar": "أرسلنا طلبك إلى المصانع",
        "body_en": "We'll tell you as soon as a manufacturer replies.",
        "body_ar": "سنخبرك فور رد أحد المصانع.",
    },
    "clarifying": {
        "title_en": "The manufacturer is confirming details", "title_ar": "المصنع يؤكد التفاصيل",
        "body_en": "We answer the manufacturer from your confirmed summary.",
        "body_ar": "نجيب المصنع من ملخصك المؤكد.",
    },
    "quote_received": {
        "title_en": "A manufacturer sent a quote", "title_ar": "أرسل أحد المصانع عرضاً",
        "body_en": "Our team is preparing your quote.", "body_ar": "فريقنا يجهّز عرض السعر لك.",
    },
    "quote_review": {"title_en": "Your quote is ready", "title_ar": "عرض السعر جاهز"},
    "awaiting_payment": {"title_en": "Waiting for your payment", "title_ar": "بانتظار دفعتك"},
    "sample_in_transit": {"title_en": "Your sample is on its way", "title_ar": "عينتك في الطريق"},
    "sample_review": {"title_en": "Your sample is ready to review", "title_ar": "عينتك جاهزة للمراجعة"},
    "in_production": {"title_en": "Production started", "title_ar": "بدأ التصنيع"},
    "shipped": {"title_en": "Your order shipped", "title_ar": "تم شحن طلبك"},
    "customs_paperwork": {"title_en": "Customs paperwork in progress", "title_ar": "أوراق الجمارك قيد التجهيز"},
    "delivered": {"title_en": "Your order was delivered", "title_ar": "تم تسليم طلبك"},
    "expired": {"title_en": "Your quote expired", "title_ar": "انتهت صلاحية عرض السعر"},
    "refunded": {"title_en": "Your refund was issued", "title_ar": "تم إصدار استردادك"},
}


def status_label(stage: str) -> dict[str, str]:
    return STATUS_LABELS.get(stage, {"en": "In progress", "ar": "قيد التنفيذ"})


def stage_owner(stage: str) -> Optional[str]:
    return STAGE_OWNER.get(stage, "orion")
