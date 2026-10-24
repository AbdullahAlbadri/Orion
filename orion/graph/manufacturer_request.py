"""Quote request to a manufacturer, rendered in code from the frozen spec's Chinese translation."""

from orion.spec import QUANTITY_ID, SIZE_TABLE_ID, ProductSpec

NOT_TRANSLATED = {QUANTITY_ID, SIZE_TABLE_ID}


def render_request(spec: ProductSpec, spec_zh: dict) -> str:
    lines = [
        "您好！我们是 Orion（沙特阿拉伯）。我们的客户需要定制以下产品，请确认能否生产，并回复：",
        "1) 单价、币种、是否含税、是否含运费（或贸易条款 EXW/FOB 等）",
        "2) 起订量  3) 打样费用和时间  4) 大货交期",
        "",
        f"产品：{spec_zh['product_zh']}",
        f"总数量：{spec.quantity} 件",
    ]
    sizes = spec.answers.get(SIZE_TABLE_ID)
    if sizes:
        lines.append("尺码数量：" + "，".join(f"{size} {qty}" for size, qty in sizes.items()))
    lines.append("规格：")
    lines += [f"- {f['label_zh']}：{f['value_zh']}" for f in spec_zh["fields"]]
    lines += ["", "如有任何问题请随时告诉我们，谢谢！"]
    return "\n".join(lines)


def render_reminder(spec_zh: dict) -> str:
    return (
        f"您好，想跟进一下我们之前发送的「{spec_zh['product_zh']}」询价。"
        "方便的话请回复报价、起订量和交期，谢谢！"
    )
