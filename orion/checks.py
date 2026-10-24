"""Step 1 environment checks: Postgres reachable, Claude reachable through OpenRouter.

Run with:  uv run python -m orion.checks
"""

import asyncio
import sys

import psycopg
from langchain_openai import ChatOpenAI

from orion.config.settings import get_settings


async def check_postgres(database_url: str) -> str:
    async with await psycopg.AsyncConnection.connect(database_url) as conn:
        row = await (await conn.execute("select version()")).fetchone()
        return row[0].split(",")[0]


async def check_openrouter(api_key: str, base_url: str, model: str) -> str:
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is empty in .env")
    llm = ChatOpenAI(model=model, api_key=api_key, base_url=base_url, max_tokens=20)
    reply = await llm.ainvoke("Reply with exactly: Orion online")
    return reply.content


async def main() -> int:
    settings = get_settings()
    checks = {
        "Postgres": check_postgres(settings.database_url),
        f"OpenRouter ({settings.consultant_model})": check_openrouter(
            settings.openrouter_api_key.get_secret_value(),
            settings.openrouter_base_url,
            settings.consultant_model,
        ),
    }
    results = await asyncio.gather(*checks.values(), return_exceptions=True)

    failed = False
    for name, result in zip(checks, results):
        if isinstance(result, Exception):
            failed = True
            print(f"FAIL  {name}: {type(result).__name__}: {result}")
        else:
            print(f"OK    {name}: {result}")
    return 1 if failed else 0


if __name__ == "__main__":
    # psycopg's async mode needs a selector event loop; Windows defaults to proactor.
    sys.exit(asyncio.run(main(), loop_factory=asyncio.SelectorEventLoop))
