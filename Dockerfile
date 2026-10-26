# The Orion backend: the API and the background worker run from this one image (see docker-compose.prod.yml).
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1

# Dependencies first, so code changes do not reinstall them
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY orion ./orion
COPY alembic.ini ./
RUN uv sync --frozen --no-dev

# Runs as a normal user; uploads live in /data (a volume)
RUN useradd --create-home --uid 1000 orion && mkdir -p /data/uploads && chown -R orion /data /app
USER orion

EXPOSE 8100
CMD ["uv", "run", "--no-sync", "python", "-m", "orion.api", "--host", "0.0.0.0", "--port", "8100"]
