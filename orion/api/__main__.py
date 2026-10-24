"""Run the API:  uv run python -m orion.api [--host 127.0.0.1] [--port 8000]

Uses a selector event loop, which psycopg's async mode needs on Windows.
"""

import argparse
import asyncio
import logging

import uvicorn

from orion.api.app import create_app


def main() -> None:
    parser = argparse.ArgumentParser(prog="orion.api")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    server = uvicorn.Server(uvicorn.Config(create_app(), host=args.host, port=args.port, log_level="info"))
    asyncio.run(server.serve(), loop_factory=asyncio.SelectorEventLoop)


if __name__ == "__main__":
    main()
