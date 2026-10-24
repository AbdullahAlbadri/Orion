"""Terminal chat for trying the ordering graph with the real LLM.

    uv run python -m orion.cli                       # in-memory, lost on exit
    uv run python -m orion.cli --postgres            # saved in Postgres
    uv run python -m orion.cli --postgres --order ID # resume a saved order
"""

import argparse
import asyncio
import json
import sys
import uuid
from contextlib import AsyncExitStack

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from orion.config.settings import get_settings
from orion.graph.graph import build_graph, get_order, send_reply, start_order
from orion.tools.llm import OpenRouterConsultant


def ask(label: str) -> str:
    return input(f"{label}> ").strip()


def answer_prompt(prompt: dict):
    """Show a pending prompt and turn what the user types into a reply."""
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


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--postgres", action="store_true", help="save the order in Postgres")
    parser.add_argument("--order", help="order id to resume (with --postgres)")
    args = parser.parse_args()

    settings = get_settings()
    consultant = OpenRouterConsultant(
        settings.openrouter_api_key.get_secret_value(), settings.openrouter_base_url, settings.consultant_model
    )

    async with AsyncExitStack() as stack:
        if args.postgres:
            checkpointer = await stack.enter_async_context(AsyncPostgresSaver.from_conn_string(settings.database_url))
            await checkpointer.setup()  # creates the checkpoint tables on first run
        else:
            checkpointer = InMemorySaver()
        app = build_graph(consultant, checkpointer)

        order_id = args.order or f"order-{uuid.uuid4().hex[:8]}"
        if args.order:
            prompt = (await get_order(app, order_id)).get("pending")
        else:
            prompt = await start_order(app, order_id)
        print(f"Order {order_id}  (Ctrl+C to stop)")

        while prompt:
            prompt = await send_reply(app, order_id, answer_prompt(prompt))

        order = await get_order(app, order_id)
        print(f"\nDone. Stage: {order['stage']}")
        print(json.dumps(order["spec"], ensure_ascii=False, indent=2))
        if order.get("needs_human"):
            print(f"Flagged for the team: {order['needs_human']}")


if __name__ == "__main__":
    try:
        # psycopg's async mode needs a selector event loop; Windows defaults to proactor.
        asyncio.run(main(), loop_factory=asyncio.SelectorEventLoop)
    except KeyboardInterrupt:
        sys.exit(0)
