"""Terminal chat for trying the order graph with the real LLM.

    uv run python -m orion.cli                       # in-memory; you also play the manufacturer
    uv run python -m orion.cli --postgres            # saved in Postgres; manufacturers via orion.relay
    uv run python -m orion.cli --postgres --order ID # resume a saved order
"""

import argparse
import asyncio
import json
import sys
import uuid
from contextlib import asynccontextmanager

from langgraph.checkpoint.memory import InMemorySaver

from orion.config.settings import get_settings
from orion.db.stores import InMemoryDirectory, InMemoryOutbox, InMemoryPriceStore, InMemoryScheduler, Manufacturer
from orion.deps import Deps, openrouter_agents
from orion.graph.graph import build_graph, get_order, on_event, send_reply, start_order, waiting_on
from orion.relay import print_order, read_pasted_text
from orion.runtime import manual_event_id, open_postgres_app

DEV_MANUFACTURER = Manufacturer(id="dev-factory", name="Dev Factory (you)")


def ask(label: str) -> str:
    return input(f"{label}> ").strip()


def answer_prompt(prompt: dict):
    """Show a pending customer prompt and turn what the user types into a reply."""
    print()
    if prompt.get("error"):
        print(f"! {prompt['error']}")

    if prompt["kind"] == "choice":
        print(prompt["prompt"])
        for i, option in enumerate(prompt["options"], start=1):
            print(f"  {i}. {option['name']}")
        return {"choice": ask("number or name")}

    if prompt["kind"] == "form":
        print(prompt["prompt"])
        answers = {}
        for q in prompt["questions"]:
            current = prompt["values"].get(q["id"])
            if current is not None and q["id"] not in prompt["errors"]:
                continue
            if q["id"] in prompt["errors"]:
                print(f"  ! {prompt['errors'][q['id']]}")
            line = q["prompt"] + ("" if q["required"] else " (optional, Enter to skip)")
            if q["choices"]:
                line += f" [{' / '.join(q['choices'])}]"
            if q.get("hint"):
                line += f"\n    {q['hint']}"
            print(f"- {line}")
            answers[q["id"]] = ask("  ")
        return {"answers": answers}

    if prompt["kind"] == "chat":
        print(f"Orion: {prompt['message']}")
        return {"message": ask("you")}

    if prompt["kind"] == "confirm":
        print(prompt["pre_receipt"])
        print()
        text = ask("Type 'yes' to confirm, or describe what to change")
        if text.lower() in ("yes", "y", "نعم"):
            return {"confirm": True}
        return {"confirm": False, "changes": text}

    raise ValueError(f"unknown prompt kind {prompt['kind']}")


@asynccontextmanager
async def open_memory_app(settings):
    consultant, manufacturer_agent = openrouter_agents(settings)
    deps = Deps(
        consultant=consultant,
        manufacturer_agent=manufacturer_agent,
        directory=InMemoryDirectory({("apparel", None): [DEV_MANUFACTURER]}),
        prices=InMemoryPriceStore(),
        channel=InMemoryOutbox(),
        scheduler=InMemoryScheduler(),   # no worker in memory mode: deadlines are recorded, never fired
    )
    yield build_graph(deps, InMemorySaver()), deps, None


async def play_manufacturer(app, deps: Deps, order_id: str) -> bool:
    """In-memory mode: show queued messages and let the user reply as the manufacturer. False = stop."""
    for message in deps.channel.pending():
        print("\n--- Message to the manufacturer " + "-" * 28)
        print(message["text"])
        message["status"] = "sent"
    print("-" * 60)
    text = read_pasted_text()
    if not text:
        return False
    await on_event(app, order_id, {
        "type": "manufacturer_reply",
        "event_id": manual_event_id(order_id, DEV_MANUFACTURER.id, text),
        "manufacturer_id": DEV_MANUFACTURER.id,
        "text": text,
    })
    print()
    print_order(await get_order(app, order_id))
    return True


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--postgres", action="store_true", help="save the order in Postgres")
    parser.add_argument("--order", help="order id to resume (with --postgres)")
    args = parser.parse_args()

    settings = get_settings()
    opener = open_postgres_app(settings) if args.postgres else open_memory_app(settings)
    async with opener as (app, deps, _pool):
        order_id = args.order or f"order-{uuid.uuid4().hex[:8]}"
        prompt = await waiting_on(app, order_id) if args.order else await start_order(app, order_id)
        print(f"Order {order_id}  (Ctrl+C to stop)")

        while prompt and prompt["kind"] != "waiting":
            prompt = await send_reply(app, order_id, answer_prompt(prompt))

        order = await get_order(app, order_id)
        print(f"\nSpec frozen. Stage: {order['stage']}")
        print(json.dumps(order["spec"], ensure_ascii=False, indent=2))

        if args.postgres:
            print(f"\nThe order now waits on manufacturers. Team: uv run python -m orion.relay outbox")
            return
        print("\nYou are now the manufacturer (empty message to stop).")
        while await play_manufacturer(app, deps, order_id):
            pass


if __name__ == "__main__":
    try:
        # psycopg's async mode needs a selector event loop; Windows defaults to proactor.
        asyncio.run(main(), loop_factory=asyncio.SelectorEventLoop)
    except KeyboardInterrupt:
        sys.exit(0)
