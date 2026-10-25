"""Manufacturer email: reading replies out of real-world mail, and the email channel + inbox pass against
the `orion_test` Postgres with a fake mailbox (nothing is sent)."""

import uuid

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from conftest import HOODIE_ANSWERS, ScriptedConsultant, ScriptedManufacturerAgent, turn
from orion.db.postgres import EmailRelayChannel, PostgresDirectory, PostgresPriceStore, PostgresScheduler, make_pool
from orion.db.stores import Manufacturer
from orion.deps import Deps
from orion.graph.graph import build_graph, get_order, send_reply, start_order
from orion.tools.channel import OutgoingMessage
from orion.tools.mail import IncomingMail, order_tag, parse, reply_text, subject_for
from orion.tools.manufacturer_llm import ReplyAnalysis
from orion.tools.prices import ExtractedPrice
from orion.worker import read_inbox

QUOTE = "单价45元/件，含税，起订量100件"


def test_reply_text_drops_the_quoted_conversation():
    gmail = f"{QUOTE}\n\nOn Sun, Oct 25, 2026 at 3:00 PM Orion <orion@example.com>\nwrote:\n> 您好！我们是 Orion"
    assert reply_text(gmail) == QUOTE
    chinese_gmail = f"{QUOTE}\n\nOrion <orion@example.com> 于2026年10月25日周日 15:00写道：\n> 您好"
    assert reply_text(chinese_gmail) == QUOTE
    qq = f"{QUOTE}\n------------------ 原始邮件 ------------------\n发件人: Orion\n单价 1 元"
    assert reply_text(qq) == QUOTE
    assert reply_text("x" * 10000) == "x" * 8000


def test_parse_reads_sender_tag_html_and_the_servers_verdict():
    raw = (
        "Authentication-Results: mx.google.com; dkim=pass header.i=@163.com; spf=pass\r\n"
        "Authentication-Results: forged; dkim=pass\r\n"
        "From: =?utf-8?b?5bel5Y6C?= <Sales@Factory.example>\r\n"
        f"Subject: Re: {subject_for('ord_0123456789ab')}\r\n"
        "Message-ID: <abc@factory.example>\r\n"
        "Content-Type: text/html; charset=utf-8\r\n\r\n"
        "<div>单价45元/件<br>起订量100件</div><div>发件人: Orion</div>"
    ).encode()
    mail = parse("7", raw)
    assert mail.sender == "sales@factory.example" and mail.authenticated
    assert order_tag(mail.subject) == "ord_0123456789ab"
    assert mail.text == "单价45元/件\n起订量100件"
    # Only the first Authentication-Results header counts (ours); a sender can add others lower down
    forged = raw.replace(b"mx.google.com; dkim=pass header.i=@163.com; spf=pass", b"mx.google.com; spf=fail")
    assert not parse("8", forged).authenticated


class FakeMailbox:
    def __init__(self):
        self.sent: list[dict] = []
        self.mail: list[IncomingMail] = []
        self.handled: dict[str, bool] = {}     # uid -> starred
        self.fail = False

    async def send(self, to, subject, text):
        if self.fail:
            raise OSError("smtp down")
        self.sent.append({"to": to, "subject": subject, "text": text})

    async def unread(self, limit=20):
        return [m for m in self.mail if m.uid not in self.handled][:limit]

    async def done(self, uid, flag=False):
        self.handled[uid] = flag


async def test_email_manufacturer_gets_the_request_and_its_reply_resumes_the_order(pg_url):
    run = uuid.uuid4().hex[:12]
    order_id, market = f"ord_{run}", f"m-{run}"
    factory = Manufacturer(id=f"mail-{run}", name="Mail Factory", contact=f" Sales-{run}@Factory.example ", channel="email")
    agent = ScriptedManufacturerAgent(analyses=[ReplyAnalysis(
        kind="quote", summary_en="45 CNY",
        prices=[ExtractedPrice(unit_price=45, currency="元", unit="piece", quantity=150, tax_included=True,
                               quoted_text="单价45元/件")],
    )])
    mailbox = FakeMailbox()

    async with make_pool(pg_url) as pool:
        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()
        directory, channel = PostgresDirectory(pool), EmailRelayChannel(pool, mailbox)
        await directory.add(factory)
        await directory.assign(factory.id, market, None, 1)

        class Directory:   # this order's market only reaches our factory
            async def ranked_for(self, _market, option):
                return await directory.ranked_for(market, option)

        app = build_graph(Deps(
            consultant=ScriptedConsultant([turn("Done.", ready=True)], []), manufacturer_agent=agent,
            directory=Directory(), prices=PostgresPriceStore(pool), channel=channel, scheduler=PostgresScheduler(pool),
        ), checkpointer)
        await start_order(app, order_id)
        for reply in ({"choice": "apparel"}, {"choice": "hoodie"}, {"answers": HOODIE_ANSWERS}, {"confirm": True}):
            await send_reply(app, order_id, reply)

        # The request went out by email with the order tag, and is not left in the outbox
        [sent] = mailbox.sent
        assert sent["to"] == f"Sales-{run}@Factory.example" and order_tag(sent["subject"]) == order_id
        assert "卫衣" in sent["text"]
        assert not [m for m in await channel.pending() if m["order_id"] == order_id]

        def mail(uid, sender=f"sales-{run}@factory.example", subject=f"Re: {sent['subject']}", ok=True, msg_id=None):
            return IncomingMail(uid=uid, message_id=msg_id or f"<{uid}@factory.example>", sender=sender,
                                subject=subject, text=QUOTE, authenticated=ok)

        mailbox.mail = [
            mail("1"),
            mail("2", msg_id="<1@factory.example>"),                 # the same email delivered twice
            mail("3", sender="someone@else.example"),                # unknown sender
            mail("4", ok=False),                                     # From address not verified
            mail("5", subject="Re: hello"),                          # no order tag
        ]
        counts = await read_inbox(app, mailbox, channel, pool)
        assert counts == {"processed": 2, "for_team": 3}
        assert agent.analyzed == [QUOTE]                              # processed once
        assert mailbox.handled == {"1": False, "2": False, "3": True, "4": True, "5": True}
        state = await get_order(app, order_id)
        assert state["stage"] == "quote_received" and state["quotes"][0]["manufacturer_id"] == factory.id


async def test_failed_email_stays_in_the_outbox_and_manual_manufacturers_are_never_emailed(pg_url):
    run = uuid.uuid4().hex[:12]
    mailbox = FakeMailbox()
    async with make_pool(pg_url) as pool:
        directory, channel = PostgresDirectory(pool), EmailRelayChannel(pool, mailbox)
        await directory.add(Manufacturer(id=f"e-{run}", name="E", contact="e@factory.example", channel="email"))
        await directory.add(Manufacturer(id=f"w-{run}", name="W", contact="WeChat: abc"))
        await channel.deliver(OutgoingMessage(id=f"{run}:w", order_id=f"ord_{run}", manufacturer_id=f"w-{run}", text="hi"))
        mailbox.fail = True
        await channel.deliver(OutgoingMessage(id=f"{run}:e", order_id=f"ord_{run}", manufacturer_id=f"e-{run}", text="hi"))
        assert mailbox.sent == []
        assert {m["id"] for m in await channel.pending()} >= {f"{run}:w", f"{run}:e"}

        # A retried step re-delivers the same message id: sent now, and never twice
        mailbox.fail = False
        await channel.deliver(OutgoingMessage(id=f"{run}:e", order_id=f"ord_{run}", manufacturer_id=f"e-{run}", text="hi"))
        await channel.deliver(OutgoingMessage(id=f"{run}:e", order_id=f"ord_{run}", manufacturer_id=f"e-{run}", text="hi"))
        assert [m["to"] for m in mailbox.sent] == ["e@factory.example"]
        assert f"{run}:e" not in {m["id"] for m in await channel.pending()}
