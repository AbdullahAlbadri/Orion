"""Run the API:  uv run python -m orion.api [--reload] [--host 127.0.0.1] [--port 8000]

--reload (development): restarts automatically whenever code under orion/ changes, so the running API never
lags behind the code. Both modes use a selector event loop, which psycopg's async mode needs on Windows
(uvicorn picks it itself when it runs the server in a subprocess, as --reload does).
"""

import argparse
import asyncio
import logging
from pathlib import Path

import uvicorn

from orion.api.app import create_app


def main() -> None:
    parser = argparse.ArgumentParser(prog="orion.api")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true", help="restart when code changes (development)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if args.reload:
        uvicorn.run(
            "orion.api.app:create_app", factory=True, reload=True,
            reload_dirs=[str(Path(__file__).resolve().parents[1])],
            host=args.host, port=args.port, log_level="info",
        )
        return
    server = uvicorn.Server(uvicorn.Config(create_app(), host=args.host, port=args.port, log_level="info"))
    asyncio.run(server.serve(), loop_factory=asyncio.SelectorEventLoop)


if __name__ == "__main__":
    main()
