# Orion backend (أوريون)

Orion is a middle-man platform for new business owners in Saudi Arabia. A customer describes a custom product through an AI-guided ordering flow; Orion then handles the manufacturers (mostly in China), shipping and customs paperwork on their behalf.

This repo is the **LangGraph backend** that replaces the earlier n8n prototype (kept in a separate repo as reference only).

> **Status:** early build. The ordering graph works end to end in tests; the manufacturer layer, API and deployment are next. See [Build order](#build-order).

## Docs

| File | What it covers |
|---|---|
| [docs/DESIGN.md](docs/DESIGN.md) | Ordering flow, spec schema, markets, manufacturer layer, memory, pricing, events/timers, stages, scaling, deployment |
| [docs/DECISIONS.md](docs/DECISIONS.md) | What is decided, which defaults are policy flags, what is still open |
| [CLAUDE.md](CLAUDE.md) | Hard rules, layout and current task (also read by Claude Code) |

## How it works (short version)

```
select_market → pick_option → mandatory_questions
  → deep_dive (AI closes gaps) ⇄ completeness_check
  → pre_receipt → customer_confirm → FREEZE spec
  → translate → manufacturer ⇄ verify loop
  → notify customer → shipping tracker
```

- Each order is one LangGraph thread (`thread_id` = order id). The order sleeps as a Postgres checkpoint until an event (customer message, manufacturer reply, payment webhook, timeout) resumes it.
- Markets and their questions are **config**, not code.
- The **frozen product spec** is the source of truth for receipts, translations and manufacturer checks.
- **The AI never discusses or negotiates price.** Prices are extracted and verified in code, and a code check blocks any outgoing manufacturer message containing prices.

## Stack

| Layer | Choice |
|---|---|
| Orchestration | LangGraph + LangChain components |
| LLMs | OpenRouter (Claude for the consultant, a cheaper model for classification) |
| Database | Postgres (checkpointer, long-term store, business tables) |
| API | FastAPI (async, streaming) |
| Deploy | Hetzner, Docker Compose, Caddy; API at `api.orionagentic.online` |
| Tooling | Python 3.11+, `uv`, pytest |

## Project layout

```
orion/
  graph/     state, nodes, graph wiring
  tools/     email, db lookups, price extraction, translation
  api/       FastAPI routes, auth, webhooks
  db/        connection, migrations (Alembic)
  config/    markets, policy
tests/
docs/        design docs, legacy/ (prompts mined from the n8n repo)
docker-compose.yml
pyproject.toml
.env.example
```

## Getting started

Prerequisites: Python 3.12+, [uv](https://docs.astral.sh/uv/), Docker Desktop (running), an OpenRouter API key.

```bash
# 1. Install dependencies into .venv
uv sync

# 2. Configure secrets
cp .env.example .env          # then fill in OPENROUTER_API_KEY

# 3. Start local Postgres (pgvector image, host port 5433)
docker compose up -d postgres

# 4. Check Postgres and OpenRouter are reachable
uv run python -m orion.checks
```

Expected output of step 4:

```
OK    Postgres: PostgreSQL 17.x
OK    OpenRouter (anthropic/claude-sonnet-4.5): Orion online
```

## Running

```bash
uv run pytest                                      # full ordering flow with a scripted fake LLM
uv run python -m orion.cli                         # chat with the real LLM in the terminal (in-memory)
uv run python -m orion.cli --postgres              # same, but the order is saved in Postgres
uv run python -m orion.cli --postgres --order ID   # resume a saved order
```

## Code map

| File | Role |
|---|---|
| `orion/spec.py` | `ProductSpec`, `Question`, answer validation (incl. size-by-quantity tables) |
| `orion/config/markets.py` | Market registry; fashion & apparel is the first market |
| `orion/config/policy.py` | `Policy` flags with defaults (`TODO(decide)`) |
| `orion/graph/nodes.py` | Ordering-flow nodes as plain functions |
| `orion/graph/graph.py` | LangGraph wiring, plus `start_order` / `send_reply` / `get_order` |
| `orion/graph/pre_receipt.py` | Pre-receipt rendered from the spec (code, not LLM) |
| `orion/tools/llm.py`, `prompts.py` | `Consultant` interface and the OpenRouter implementation |

Customer interaction contract: the graph pauses with a `pending` prompt (`kind` = `choice`, `form`, `chat` or `confirm`), and the caller resumes it with `{"choice": ...}`, `{"answers": {...}}`, `{"message": ...}` or `{"confirm": bool, "changes": ...}`.

`.env` is gitignored; only `.env.example` is committed. This backend uses its own database, keys, Compose project name and ports, kept separate from the n8n system.

## Build order

1. [ ] Environment checks: local Postgres up, Claude reachable through OpenRouter
2. [x] Spec schema and the first market config (fashion & apparel)
3. [x] Ordering graph: market → option → mandatory questions → AI gap-closing → pre-receipt → freeze spec (tested with a fake LLM; real-LLM run pending)
4. [ ] Manufacturer node with manual relay, price extraction, price dataset
5. [ ] Event handler and timers (3-day manufacturer timeout, quote expiry)
6. [ ] API and auth, then website connection
7. [ ] Real email / WeCom channels, stats page, deployment
8. [ ] Paperwork graph (separate)

## Open decisions

Unresolved choices are implemented as policy flags with defaults and marked `# TODO(decide)` in code. The full list is in [docs/DECISIONS.md](docs/DECISIONS.md).
