from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from orion.config.settings import get_settings

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _url() -> str:
    # A caller (e.g. the tests) may set sqlalchemy.url; otherwise use DATABASE_URL.
    url = config.get_main_option("sqlalchemy.url") or get_settings().database_url
    # SQLAlchemy needs the driver named explicitly to use psycopg 3
    return url.replace("postgresql://", "postgresql+psycopg://", 1)


def run_migrations_offline() -> None:
    context.configure(url=_url(), literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
