"""Quote request to a manufacturer, rendered in code from the frozen spec and its Chinese translation.

Chinese first, then the same request in English. Details are grouped like the customer's form (design,
quantity, quality); placements are described in code and files go with the message as attachments, so
neither depends on the translation. The text must pass the price guard: it asks for a quote, never states one.
"""

from typing import Any

from orion.config.markets import MARKETS, get_questions
from orion.graph.pre_receipt import _humanize, build_summary
from orion.spec import QUANTITY_ID, SIZE_TABLE_ID, ProductSpec, describe_placement, is_file_list, is_placement_list

NOT_TRANSLATED = {QUANTITY_ID, SIZE_TABLE_ID}

SECTIONS = {
    "zh": {"design": "一、款式与设计", "quantity": "二、数量、尺码与交期", "quality": "三、面料、工艺与包装"},
    "en": {"design": "A. Design", "quantity": "B. Quantity, sizes and timing", "quality": "C. Fabric, finishing and packing"},
}


def not_translated(spec: ProductSpec) -> set[str]:
    """Answers the translation skips: quantities, sizes, files and placements are written in code."""
    return NOT_TRANSLATED | {qid for qid, v in spec.answers.items() if is_file_list(v) or is_placement_list(v)}


def request_files(spec: ProductSpec) -> list[dict]:
    """Every uploaded file in the answers, once each, in answer order: sent as attachments."""
    files: dict[str, dict] = {}
    for value in spec.answers.values():
        if is_file_list(value):
            for f in value:
                files.setdefault(f["file_id"], f)
    return list(files.values())


def render_request(spec: ProductSpec, spec_zh: dict, order_id: str = "") -> str:
    questions = get_questions(spec.market, spec.option)
    form_ids = {q.id for q in questions}
    summary = build_summary(spec, MARKETS[spec.market], questions, "en")
    zh = {f["id"]: f for f in spec_zh["fields"]}
    number = {f["file_id"]: n for n, f in enumerate(request_files(spec), start=1)}

    def value(item: dict, lang: str) -> str:
        raw: Any = item["raw"]
        if is_file_list(raw):
            word = "附件" if lang == "zh" else "attachment "
            return ("、" if lang == "zh" else ", ").join(f"{word}{number[f['file_id']]} ({f['name']})" for f in raw)
        if is_placement_list(raw):
            word = "附件" if lang == "zh" else "attachment "
            return ("；" if lang == "zh" else "; ").join(
                describe_placement(p, lang) + (f" ({word}{number[p['file_id']]})" if p.get("file_id") in number else "")
                for p in raw)
        if lang == "zh" and item["id"] in zh:
            return zh[item["id"]]["value_zh"]
        if lang == "en" and item["id"] not in form_ids and zh.get(item["id"], {}).get("value_en"):
            return zh[item["id"]]["value_en"]   # the AI's questions were answered in the customer's language
        return item["value"]

    def name(item: dict, lang: str) -> str:
        field = zh.get(item["id"])
        if lang == "zh":
            return field["label_zh"] if field and field["label_zh"] and field["label_zh"] != item["id"] else item["label"]
        return _humanize(item["id"])   # ids are short English: "decoration_placement" -> "Decoration placement"

    sizes = spec.answers.get(SIZE_TABLE_ID) or {}
    files = request_files(spec)
    ref_zh, ref_en = (f"（订单号 {order_id}）", f" (order {order_id})") if order_id else ("", "")

    lines = [
        f"【询价单】{spec_zh['product_zh']}{ref_zh}",
        "",
        "您好！我们是 Orion，一家沙特阿拉伯的采购公司。我们的客户需要定制以下产品，"
        "请确认能否按要求生产，并按文末的问题回复报价。",
        "",
        f"产品：{spec_zh['product_zh']}",
        f"总数量：{spec.quantity} 件",
    ]
    if sizes:
        lines.append("尺码分配：" + "，".join(f"{size} × {qty}" for size, qty in sizes.items()))
    for section in summary["sections"]:
        lines += ["", SECTIONS["zh"][section["id"]]]
        lines += [f"{i}. {name(item, 'zh')}：{value(item, 'zh')}" for i, item in enumerate(section["items"], 1)]
    if files:
        lines += ["", "附件（随本邮件发送）："] + [f"附件{n}：{f['name']}" for n, f in enumerate(files, 1)]
    lines += [
        "",
        "请回复以下信息：",
        "1. 单价（请注明币种、是否含税、贸易条款如 EXW / FOB）",
        "2. 最小起订量（MOQ）",
        "3. 打样费用和打样时间",
        "4. 大货生产周期",
        "5. 运到沙特阿拉伯的运费和运输时间（请注明海运或空运、是否到门、是否包含清关和关税）",
        "如有任何问题，请直接回复本邮件，并保留邮件标题中的订单号。谢谢！",
        "",
        "-" * 40,
        "English version",
        "",
        f"Request for quotation: {summary['product']}{ref_en}",
        "",
        "Hello! We are Orion, a sourcing company in Saudi Arabia. Our client needs the custom product below. "
        "Please confirm you can make it exactly as described, and reply with the information listed at the end.",
        "",
        f"Product: {summary['product']}",
        f"Total quantity: {spec.quantity} pcs",
    ]
    if sizes:
        lines.append("Sizes: " + ", ".join(f"{size} x {qty}" for size, qty in sizes.items()))
    for section in summary["sections"]:
        lines += ["", SECTIONS["en"][section["id"]]]
        lines += [f"{i}. {name(item, 'en')}: {value(item, 'en')}" for i, item in enumerate(section["items"], 1)]
    if files:
        lines += ["", "Attachments (sent with this email):"] + [f"Attachment {n}: {f['name']}" for n, f in enumerate(files, 1)]
    lines += [
        "",
        "Please reply with:",
        "1. Unit price (currency, whether tax is included, and the incoterm such as EXW / FOB)",
        "2. Minimum order quantity (MOQ)",
        "3. Sample cost and sample lead time",
        "4. Mass production lead time",
        "5. Shipping cost and transit time to Saudi Arabia (sea or air, to the door or not, customs and duties "
        "included or not)",
        "If anything is unclear, just reply to this email and keep the order number in the subject. Thank you!",
    ]
    return "\n".join(lines)


def render_reminder(spec_zh: dict) -> str:
    return (
        f"您好，想跟进一下我们之前发送的「{spec_zh['product_zh']}」询价。"
        "方便的话请回复报价、起订量和交期，谢谢！\n\n"
        f"Hello, a quick follow-up on our quotation request for {spec_zh['product_zh']}. "
        "Please reply with your quote, MOQ and lead time when you can. Thank you!"
    )
