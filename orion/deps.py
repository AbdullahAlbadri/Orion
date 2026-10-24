"""Everything the graph needs from the outside world, built for tests, local runs or Postgres."""

from dataclasses import dataclass

from psycopg_pool import AsyncConnectionPool

from orion.config.settings import Settings
from orion.db.stores import ManufacturerDirectory, PriceStore, Scheduler
from orion.tools.channel import Channel
from orion.tools.llm import Consultant, OpenRouterConsultant
from orion.tools.manufacturer_llm import ManufacturerAgent, OpenRouterManufacturerAgent


@dataclass
class Deps:
    consultant: Consultant
    manufacturer_agent: ManufacturerAgent
    directory: ManufacturerDirectory
    prices: PriceStore
    channel: Channel
    scheduler: Scheduler


def openrouter_agents(settings: Settings) -> tuple[Consultant, ManufacturerAgent]:
    key = settings.openrouter_api_key.get_secret_value()
    return (
        OpenRouterConsultant(key, settings.openrouter_base_url, settings.consultant_model),
        OpenRouterManufacturerAgent(key, settings.openrouter_base_url, settings.manufacturer_model),
    )


def postgres_deps(settings: Settings, pool: AsyncConnectionPool) -> Deps:
    from orion.db.postgres import ManualRelayChannel, PostgresDirectory, PostgresPriceStore, PostgresScheduler

    consultant, manufacturer_agent = openrouter_agents(settings)
    return Deps(
        consultant=consultant,
        manufacturer_agent=manufacturer_agent,
        directory=PostgresDirectory(pool),
        prices=PostgresPriceStore(pool),
        channel=ManualRelayChannel(pool),
        scheduler=PostgresScheduler(pool),
    )
