# Orion backend (أوريون)

Orion is a middle-man platform for new business owners in Saudi Arabia. A customer describes a custom product through an AI-guided ordering flow; Orion then handles the manufacturers (mostly in China), shipping and customs paperwork on their behalf.

This repo is the **LangGraph backend** that replaces the earlier n8n prototype (kept in a separate repo as reference only).

> **Status:** early build. Ordering, the manufacturer layer (manual relay) and timers work end to end in tests; the API and deployment are next. See [Build order](#build-order).

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

# 3. Start local Postgres (pgvector image, host port 5433) and create the business tables
docker compose up -d postgres
uv run alembic upgrade head

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
uv run pytest                                      # all tests (Postgres tests skip if it is not running)
uv run python -m orion.cli                         # order in the terminal with the real LLM; then you play the manufacturer
uv run python -m orion.cli --postgres              # same, saved in Postgres; manufacturers handled via orion.relay
uv run python -m orion.cli --postgres --order ID   # resume a saved order
```

### API and team console

```bash
uv run python -m orion.admin add-member you@example.com --role admin   # first admin (once)
uv run python -m orion.api                                             # http://localhost:8000
```

- API docs (try every endpoint): http://localhost:8000/docs
- Team console: http://localhost:8000/console/ (log in with an email code)
- Until an email service is connected, login codes are printed in the API terminal.

Login is passwordless: a one-time email code (or link), or Google / Apple sign-in once `GOOGLE_CLIENT_ID` /
`APPLE_CLIENT_ID` are set. Access tokens last 15 minutes; the refresh token is an httpOnly cookie that rotates on
every use, and replaying an old one logs that user out everywhere. Customers and team members are separate
accounts; team roles are `admin` and `agent`. Customers only see their own orders, never manufacturer data or
prices.

### Customer website (`web/`, Next.js)

```bash
cd web
copy .env.local.example .env.local     # API url + Google client id (both public)
npm install
npm run dev                            # http://localhost:3000 (the API must be running on :8000)
```

Arabic (right-to-left) by default with an English switch. Login with an email code or Google; then the ordering
flow (market → product → details form with a size table → chat → summary to confirm) and "My orders". Brand:
yellow `#FEB72F`, red `#BC3039`, navy `#11101E`, off-white `#F8F8F8`; Work Sans for Latin text. The Arabic brand
font (Swissra) is licensed, so IBM Plex Sans Arabic stands in until the licence files are added. Production
address: `app.orionagentic.online`.

### Manual relay from the terminal (same actions as the console)

```bash
uv run python -m orion.relay add-manufacturer factory-a "Factory A" --contact "WeChat: abc" --market apparel --option hoodie --rank 1
uv run python -m orion.relay outbox                       # messages to send by hand
uv run python -m orion.relay sent MESSAGE_ID              # mark one as sent
uv run python -m orion.relay reply ORDER_ID factory-a     # paste the reply; end with a line containing only .
uv run python -m orion.relay order ORDER_ID               # status, quotes and what needs a human
```

Pasting the same reply twice is safe: it gets the same event id and is processed once.

### Worker (timers)

```bash
uv run python -m orion.worker          # runs forever; fires due deadlines every 30 s
uv run python -m orion.worker --once   # one pass
```

When an order starts waiting, a node writes a row to `deadlines`; the worker turns due rows into `timeout` events.
Manufacturer reply clock: 3 China working days → one reminder → 1 more working day → next manufacturer (the
first stays open). A quote stops the clock and starts the quote expiry (7 days, placeholder). Several workers can
run at once.

China holidays live in `orion/config/china_calendar.py` (2026 from the State Council notice). **Add next year's
dates when the notice comes out (around November)**; until then a deadline in an unknown year is flagged.

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
| `orion/graph/manufacturer_nodes.py` | Translate spec, contact manufacturers in rank order, handle replies |
| `orion/graph/manufacturer_request.py` | Chinese quote request rendered in code from the spec |
| `orion/tools/price_guard.py` | Blocks prices, amounts and negotiation language in outgoing messages (rule 1) |
| `orion/tools/prices.py` | Verifies LLM-extracted prices against the message text (rule 2) |
| `orion/tools/channel.py` | Channel interface; `send_to_manufacturer` is the only send path and always runs the guard |
| `orion/tools/manufacturer_llm.py` | Translation, reply analysis and spec-only answers (untrusted input) |
| `orion/db/stores.py`, `postgres.py` | Manufacturer directory, append-only price dataset, message outbox |
| `orion/db/migrations/` | Alembic migrations |
| `orion/relay.py` | Manual relay CLI for the team |
| `orion/worker.py` | Background worker: fires due deadlines as `timeout` events |
| `orion/runtime.py` | Opens the Postgres-backed graph; per-order advisory lock (`send_event`) |
| `orion/config/china_calendar.py` | China working days and official holidays |
| `orion/api/` | FastAPI app: `auth.py` (login), `orders.py` (customer), `team.py` (team), `console/` (team page) |
| `orion/api/security.py`, `oidc.py` | Login codes, JWTs, refresh tokens; Google / Apple ID token checks |
| `orion/db/accounts.py` | Customers, team members, login codes, refresh tokens, orders table |
| `orion/admin.py` | Create team members from the terminal |

Events: `on_event(app, order_id, event)` resumes an order only if it is waiting for that event type, and `handle_manufacturer_event` ignores event ids it has already processed. Processes that resume orders (relay, worker, later the API) go through `send_event`, which holds a per-order lock so events for one order never run at the same time.

Customer interaction contract: the graph pauses with a `pending` prompt (`kind` = `choice`, `form`, `chat` or `confirm`), and the caller resumes it with `{"choice": ...}`, `{"answers": {...}}`, `{"message": ...}` or `{"confirm": bool, "changes": ...}`.

`.env` is gitignored; only `.env.example` is committed. This backend uses its own database, keys, Compose project name and ports, kept separate from the n8n system.

## Build order

1. [ ] Environment checks: local Postgres up, Claude reachable through OpenRouter
2. [x] Spec schema and the first market config (fashion & apparel)
3. [x] Ordering graph: market → option → mandatory questions → AI gap-closing → pre-receipt → freeze spec (tested with a fake LLM; real-LLM run pending)
4. [x] Manufacturer node with manual relay, price extraction, price dataset (customer quote document still to design)
5. [x] Event handler and timers (3-day manufacturer timeout with one reminder, quote expiry; customer abandonment not yet)
6. [x] API and auth, then website connection (API, login, team console, customer website; logo mark still to add)
7. [ ] Real email / WeCom channels, stats page, deployment
8. [ ] Paperwork graph (separate)

## Open decisions

Unresolved choices are implemented as policy flags with defaults and marked `# TODO(decide)` in code. The full list is in [docs/DECISIONS.md](docs/DECISIONS.md).
