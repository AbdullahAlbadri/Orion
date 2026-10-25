"""Everything the graph needs from the outside world, built for tests, local runs or Postgres."""

from dataclasses import dataclass
from typing import Optional

from psycopg_pool import AsyncConnectionPool

from orion.config.settings import Settings
from orion.db.stores import ManufacturerDirectory, PriceStore, Scheduler
from orion.tools.channel import Channel
from orion.tools.llm import Consultant, ImageLoader, OpenRouterConsultant
from orion.tools.mail import GmailMailbox
from orion.tools.manufacturer_llm import ManufacturerAgent, OpenRouterManufacturerAgent


@dataclass
class Deps:
    consultant: Consultant
    manufacturer_agent: ManufacturerAgent
    directory: ManufacturerDirectory
    prices: PriceStore
    channel: Channel
    scheduler: Scheduler


def openrouter_agents(settings: Settings, load_image: Optional[ImageLoader] = None) -> tuple[Consultant, ManufacturerAgent]:
    key = settings.openrouter_api_key.get_secret_value()
    return (
        OpenRouterConsultant(key, settings.openrouter_base_url, settings.consultant_model, load_image=load_image),
        OpenRouterManufacturerAgent(key, settings.openrouter_base_url, settings.manufacturer_model),
    )


def image_loader(settings: Settings, pool: AsyncConnectionPool) -> ImageLoader:
    """Lets the customer-side AI see pictures uploaded to the order."""
    from orion.db.accounts import AccountStore
    from orion.tools.files import LocalFileStore

    accounts, files = AccountStore(pool), LocalFileStore(settings.upload_dir)

    async def load(order_id: str, file_id: str) -> Optional[tuple[bytes, str]]:
        row = await accounts.order_file(order_id, file_id)
        if row is None:
            return None
        return files.load(row["storage_key"]), row["content_type"]

    return load


def mailbox(settings: Settings) -> Optional[GmailMailbox]:
    """The manufacturer mailbox, or None while MAIL_ADDRESS / MAIL_APP_PASSWORD are not set."""
    password = settings.mail_app_password.get_secret_value()
    if not (settings.mail_address and password):
        return None
    return GmailMailbox(settings.mail_address, password, settings.smtp_host, settings.smtp_port, settings.imap_host)


def postgres_deps(settings: Settings, pool: AsyncConnectionPool) -> Deps:
    from orion.db.postgres import EmailRelayChannel, PostgresDirectory, PostgresPriceStore, PostgresScheduler

    consultant, manufacturer_agent = openrouter_agents(settings, image_loader(settings, pool))
    return Deps(
        consultant=consultant,
        manufacturer_agent=manufacturer_agent,
        directory=PostgresDirectory(pool),
        prices=PostgresPriceStore(pool),
        channel=EmailRelayChannel(pool, mailbox(settings)),
        scheduler=PostgresScheduler(pool),
    )
