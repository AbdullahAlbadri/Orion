"""Bootstrap team accounts (the first admin cannot be created through the API).

    uv run python -m orion.admin add-member you@example.com --name "Your Name" --role admin
    uv run python -m orion.admin members
"""

import argparse
import asyncio

from orion.config.settings import get_settings
from orion.db.accounts import AccountStore
from orion.db.postgres import make_pool


async def main() -> None:
    parser = argparse.ArgumentParser(prog="orion.admin")
    sub = parser.add_subparsers(dest="command", required=True)
    add = sub.add_parser("add-member")
    add.add_argument("email")
    add.add_argument("--name")
    add.add_argument("--role", choices=["admin", "agent"], default="agent")
    sub.add_parser("members")
    args = parser.parse_args()

    async with make_pool(get_settings().database_url) as pool:
        accounts = AccountStore(pool)
        if args.command == "add-member":
            member = await accounts.add_team_member(args.email, args.name, args.role)
            print(f"Saved {member['email']} as {member['role']}. They log in with an email code at the team console.")
        else:
            for m in await accounts.list_team_members():
                print(f"{m['role']:6} {m['email']:35} {m['name'] or ''}{'' if m['active'] else '  (inactive)'}")


if __name__ == "__main__":
    asyncio.run(main(), loop_factory=asyncio.SelectorEventLoop)
