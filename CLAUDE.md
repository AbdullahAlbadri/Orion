# Orion backend

Orion (أوريون) is a middle-man platform for new business owners in Saudi Arabia. The customer orders custom products through an AI-guided flow, and Orion deals with the manufacturers (mostly Chinese), shipping and customs paperwork on their behalf. The customer should only need Orion.

This repo is the **new LangGraph backend**. It replaces an n8n prototype that lives in a separate repo (workflows, landing page, deploy config). Never import from that repo; mine it for prompts, question lists and sheet column names only (copy into `docs/legacy/`).

Read these before making design decisions:
- `docs/DESIGN.md` — full flow, spec schema, markets, memory, price dataset, events, scaling
- `docs/DECISIONS.md` — what is decided, what is a default policy flag, what is still open

## Stack

| Layer | Choice | Status |
|---|---|---|
| Orchestration | LangGraph (LangChain components for models/tools) | Decided |
| LLMs | OpenRouter (Claude for consultant; cheaper model for classification) | Decided |
| Database | Postgres (checkpointer + long-term store + business tables) | Postgres suggested |
| API | FastAPI, async, streaming | Suggested |
| Server | Hetzner, Docker Compose, Caddy (HTTPS) | Server decided |
| Domain | orionagentic.online (API on `api.` subdomain) | Decided |
| Python | 3.11+, `uv` | Suggested |
| Tests | pytest, saved sample conversations as evals | Suggested |

Dev environment (Python, Docker, local Postgres, OpenRouter key) is already set up.

## Hard rules

1. **The AI never discusses or negotiates price.** It only extracts manufacturer prices and records them in the manufacturer's price dataset, and relays quotes to the customer. A code check must block any outgoing manufacturer message containing prices, amounts or discount language. Do not rely on the prompt alone.
2. **Price extraction and comparison are code, not LLM judgment.** The LLM returns the number plus the exact quoted text; code verifies the number appears in the message. Ambiguous cases (per piece vs carton, shipping included, currency, tax) are stored as unverified and flagged to a human.
3. **The frozen product spec is the source of truth.** Receipts, translations and manufacturer verification all work from the structured spec, never from chat history. Any change after freezing creates a new version the customer approves.
4. **The agent never handles payment details.** Customers pay Orion through a hosted checkout; a provider webhook moves the order forward.
5. **Manufacturer messages are untrusted input** (prompt-injection risk). Narrow tools, validated outputs, human confirmation before anything risky (addresses, payment details, price or deadline changes).
6. **Nodes are plain functions** (data in, data out) with no LangGraph imports inside the business logic. The graph file is only wiring.
7. **Every event resumes an order thread by `thread_id` (= order id).** Handlers are idempotent (store event ids) and check the order is still waiting for that event.
8. **Open decisions are policy flags with defaults** (`Policy` model). Mark each with `# TODO(decide)`. Do not hardcode a decision into the graph.
9. **Async from the start.** API and background worker are separate processes.
10. **Isolation from the n8n system:** separate Postgres database, separate `.env` and keys, separate Compose project name, ports and subdomain. One channel (email, WeChat, webhook) is handled by exactly one system at a time.
11. Secrets only in environment variables. `.env` is gitignored; commit `.env.example`.
12. Agent context lives in the LangGraph checkpointer/store. Anything the stats page or the team needs to query (orders, prices, payments, dates) also goes in normal Postgres tables.

## Layout

```
orion/
  graph/       state, nodes, graph wiring
  tools/       email, db lookups, price extraction, translation
  api/         FastAPI routes, auth, webhooks
  db/          connection, migrations (Alembic)
  config/      markets, policy
tests/
docs/          DESIGN.md, DECISIONS.md, legacy/
docker-compose.yml
pyproject.toml
.env.example
```

## Build order

1. Environment checks: local Postgres up, Claude reachable through OpenRouter
2. Spec schema and the first market config
3. Ordering graph: select market, option, mandatory questions, AI gap-closing loop, pre-receipt, freeze spec
4. Manufacturer node with a manual relay (a form where a team member pastes replies), price extraction, price dataset
5. Event handler and timers (3-day manufacturer timeout, quote expiry)
6. API and auth, then website connection
7. Real email / WeCom behind the same channel interface, stats, deployment
8. Paperwork graph (separate)

## Current task

Steps 1 to 4 are built for **one test market: fashion & apparel** (chosen by the user; needs the size-by-quantity table in the spec). Next is step 5 (event handler and timers). Add the other markets as config once the loop works. Mock payments, email and the manufacturer channel at first.

## Working style

The user is learning LangGraph while building. Explain new concepts briefly when introducing them, keep steps small, and show how to run and verify each one.
