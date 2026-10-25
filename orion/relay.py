"""Manual relay for the team: send queued messages to manufacturers by hand and paste their replies back.

    uv run python -m orion.relay add-manufacturer factory-a "Factory A" --contact "WeChat: xyz" --market apparel --option hoodie --rank 1
    uv run python -m orion.relay add-manufacturer factory-b "Factory B" --contact sales@factory.example --channel email --market apparel
    uv run python -m orion.relay manufacturers
    uv run python -m orion.relay outbox                     # messages waiting to be sent by hand
    uv run python -m orion.relay sent MESSAGE_ID            # after you sent it
    uv run python -m orion.relay reply ORDER_ID MANUFACTURER_ID   # paste the reply, end with a line containing only .
    uv run python -m orion.relay order ORDER_ID             # what the order is doing and what needs a human
"""

import argparse
import asyncio
import json
import sys

from orion.config.settings import get_settings
from orion.db.stores import Manufacturer
from orion.graph.graph import OrderNotWaiting, get_order
from orion.runtime import manual_event_id, open_postgres_app, send_event


def read_pasted_text() -> str:
    print("Paste the manufacturer's message. Finish with a line containing only a dot (.)")
    lines = []
    for line in sys.stdin:
        if line.rstrip("\r\n") == ".":
            break
        lines.append(line.rstrip("\r\n"))
    return "\n".join(lines).strip()


def print_order(order: dict) -> None:
    spec = order.get("spec") or {}
    print(f"Order {order.get('order_id')}  stage={order.get('stage')}  "
          f"product={spec.get('option')}  qty={spec.get('quantity')}")
    for a in order.get("manufacturer_attempts", []):
        reminded = ", reminded" if a.get("reminded") else ""
        print(f"  - {a['name']} ({a['manufacturer_id']}): {a['outcome']}{reminded}, "
              f"deadline {a['deadline_at'][:16]} UTC")
    for q in order.get("quotes", []):
        print(f"  quote from {q['manufacturer_id']}: {json.dumps(q['prices'], ensure_ascii=False)}"
              f" MOQ={q['moq']} lead={q['lead_time_days']}d")
    tasks = order.get("human_tasks", [])
    if tasks:
        print("  Needs a human:")
        for t in tasks:
            print(f"    * {t['reason']}")


async def main() -> None:
    parser = argparse.ArgumentParser(prog="orion.relay")
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add-manufacturer")
    add.add_argument("id")
    add.add_argument("name")
    add.add_argument("--contact")
    add.add_argument("--channel", choices=["manual_relay", "email"], default="manual_relay",
                     help="email: messages go to --contact by email and replies are read automatically")
    add.add_argument("--market", required=True)
    add.add_argument("--option", help="omit to cover every option in the market")
    add.add_argument("--rank", type=int, default=1, help="1 = contacted first")

    sub.add_parser("manufacturers")
    sub.add_parser("outbox")
    sent = sub.add_parser("sent")
    sent.add_argument("message_id")
    reply = sub.add_parser("reply")
    reply.add_argument("order_id")
    reply.add_argument("manufacturer_id")
    show = sub.add_parser("order")
    show.add_argument("order_id")
    args = parser.parse_args()

    async with open_postgres_app(get_settings()) as (app, deps, pool):
        directory, channel = deps.directory, deps.channel

        if args.command == "add-manufacturer":
            await directory.add(Manufacturer(id=args.id, name=args.name, contact=args.contact, channel=args.channel))
            await directory.assign(args.id, args.market, args.option, args.rank)
            print(f"Saved {args.name} for {args.market}/{args.option or '*'} at rank {args.rank}")

        elif args.command == "manufacturers":
            for row in await directory.all():
                print(f"{row['market'] or '-'}/{row['option'] or '*'}  #{row['rank']}  {row['id']}  "
                      f"{row['name']}  {row['contact'] or ''}{'' if row['active'] else '  (inactive)'}")

        elif args.command == "outbox":
            messages = await channel.pending()
            if not messages:
                print("Nothing to send.")
            for m in messages:
                print("=" * 60)
                print(f"id: {m['id']}\nto: {m['manufacturer']} ({m['contact'] or 'no contact saved'})  "
                      f"order: {m['order_id']}\n")
                print(m["text"])
            if messages:
                print("=" * 60)
                print("After sending each one: uv run python -m orion.relay sent <id>")

        elif args.command == "sent":
            ok = await channel.mark_sent(args.message_id)
            print("Marked as sent." if ok else "No pending message with that id.")

        elif args.command == "reply":
            text = read_pasted_text()
            if not text:
                print("Empty message, nothing done.")
                return
            event = {
                "type": "manufacturer_reply",
                "event_id": manual_event_id(args.order_id, args.manufacturer_id, text),
                "manufacturer_id": args.manufacturer_id,
                "text": text,
            }
            try:
                await send_event(app, pool, args.order_id, event)
            except OrderNotWaiting as e:
                print(f"Not processed: {e}")
                return
            print_order(await get_order(app, args.order_id))
            if await channel.pending():
                print("\nThere are new messages to send: uv run python -m orion.relay outbox")

        elif args.command == "order":
            order = await get_order(app, args.order_id)
            if not order:
                print("No such order.")
            else:
                print_order(order)


if __name__ == "__main__":
    asyncio.run(main(), loop_factory=asyncio.SelectorEventLoop)
