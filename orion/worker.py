"""Background worker: fires due deadlines as `timeout` events into their orders, and (when the manufacturer
mailbox is configured) turns manufacturer emails into `manufacturer_reply` events.

    uv run python -m orion.worker              # run forever, checking every 30 seconds
    uv run python -m orion.worker --once       # fire what is due now and exit

Safe to run several copies: rows are claimed with FOR UPDATE SKIP LOCKED, events per order are
serialized by an advisory lock, and timeout event ids are stable across retries.
"""

import argparse
import asyncio
import hashlib
import logging
from datetime import timedelta

from psycopg_pool import AsyncConnectionPool

from orion.config.settings import get_settings
from orion.db.postgres import EmailRelayChannel, PostgresScheduler
from orion.deps import mailbox
from orion.graph.graph import OrderNotWaiting
from orion.runtime import open_postgres_app, send_event
from orion.tools.mail import Inbox, order_tag

log = logging.getLogger("orion.worker")

MAX_TRIES = 5
STUCK_AFTER = timedelta(minutes=10)


def backoff(tries: int) -> timedelta:
    return timedelta(minutes=min(2 ** tries, 60))   # 2, 4, 8, 16, 32 minutes


def timeout_event(deadline: dict) -> dict:
    return {
        "type": "timeout",
        # Same id on every retry of this firing; a reschedule bumps the generation
        "event_id": f"timeout:{deadline['id']}:{deadline['generation']}",
        "kind": deadline["kind"],
        "ref": deadline["ref"],
    }


async def fire_due(app, scheduler: PostgresScheduler, pool: AsyncConnectionPool, limit: int = 20) -> dict[str, int]:
    """One pass: claim due deadlines and resume their orders. Returns counts per outcome."""
    counts = {"fired": 0, "skipped": 0, "retry": 0, "failed": 0}
    if released := await scheduler.release_stuck(STUCK_AFTER):
        log.warning("released %d deadlines stuck in 'firing'", released)

    for deadline in await scheduler.claim_due(limit):
        order_id = deadline["order_id"]
        try:
            await send_event(app, pool, order_id, timeout_event(deadline))
        except OrderNotWaiting as e:
            # e.g. the order moved on; the node-level checks would ignore it anyway
            await scheduler.finish(deadline, "skipped", str(e))
            counts["skipped"] += 1
        except Exception as e:
            log.exception("deadline %s for order %s failed (try %d)", deadline["id"], order_id, deadline["tries"])
            if deadline["tries"] >= MAX_TRIES:
                # TODO(step 6): surface failed deadlines on the team console
                await scheduler.finish(deadline, "failed", repr(e))
                counts["failed"] += 1
            else:
                await scheduler.retry(deadline, backoff(deadline["tries"]), repr(e))
                counts["retry"] += 1
        else:
            # No-op if handling the timeout rescheduled this same deadline (e.g. after a reminder)
            await scheduler.finish(deadline, "fired")
            counts["fired"] += 1
            log.info("fired %s/%s for order %s", deadline["kind"], deadline["ref"], order_id)
    return counts


def mail_event_id(message_id: str) -> str:
    """The same email always gives the same id, so it is only processed once."""
    return "mail-" + hashlib.sha256(message_id.encode()).hexdigest()[:16]


async def read_inbox(app, inbox: Inbox, channel: EmailRelayChannel, pool: AsyncConnectionPool) -> dict[str, int]:
    """One pass over unread mail. A reply needs the order tag in its subject, a sender that is an email
    manufacturer, and a sender the mail server verified. Anything else is starred and left for the team."""
    counts = {"processed": 0, "for_team": 0}
    for mail in await inbox.unread():
        order_id = order_tag(mail.subject)
        manufacturer_id = await channel.manufacturer_for_email(mail.sender) if mail.sender else None
        if not (order_id and manufacturer_id and mail.authenticated and mail.text):
            log.warning("mail from %s (%r) not matched: order=%s manufacturer=%s verified=%s; starred for the team",
                        mail.sender, mail.subject[:80], order_id, manufacturer_id, mail.authenticated)
            await inbox.done(mail.uid, flag=True)
            counts["for_team"] += 1
            continue
        event_id = mail_event_id(mail.message_id)
        await channel.record_incoming(event_id, order_id, manufacturer_id, mail.text)
        try:
            await send_event(app, pool, order_id, {
                "type": "manufacturer_reply", "event_id": event_id, "manufacturer_id": manufacturer_id, "text": mail.text,
            })
        except OrderNotWaiting as e:
            log.warning("mail %s for order %s: %s; starred for the team", event_id, order_id, e)
            await inbox.done(mail.uid, flag=True)
            counts["for_team"] += 1
            continue
        except Exception:
            log.exception("mail %s for order %s failed; left unread to retry", event_id, order_id)
            continue
        await inbox.done(mail.uid)
        counts["processed"] += 1
        log.info("manufacturer %s replied by email to order %s", manufacturer_id, order_id)
    return counts


async def main() -> None:
    parser = argparse.ArgumentParser(prog="orion.worker")
    parser.add_argument("--once", action="store_true", help="one pass, then exit")
    parser.add_argument("--interval", type=float, default=30, help="seconds between passes")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    settings = get_settings()
    inbox = mailbox(settings)
    async with open_postgres_app(settings) as (app, deps, pool):
        scheduler = deps.scheduler
        log.info("worker started (manufacturer mailbox: %s)", settings.mail_address if inbox else "off")
        while True:
            counts = await fire_due(app, scheduler, pool)
            if any(counts.values()):
                log.info("pass: %s", counts)
            if inbox is not None:
                try:
                    mail = await read_inbox(app, inbox, deps.channel, pool)
                    if any(mail.values()):
                        log.info("mail: %s", mail)
                except Exception:
                    log.exception("reading the manufacturer mailbox failed; trying again next pass")
            if args.once:
                return
            await asyncio.sleep(args.interval)


if __name__ == "__main__":
    try:
        # psycopg's async mode needs a selector event loop; Windows defaults to proactor.
        asyncio.run(main(), loop_factory=asyncio.SelectorEventLoop)
    except KeyboardInterrupt:
        pass
