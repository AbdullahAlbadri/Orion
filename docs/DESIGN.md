# Orion backend — design

## 1. Product

Orion connects new business owners to manufacturers without the owner needing their own network. Two inner systems:

- **Manufacturer communication system**: an AI agent that knows the customer's business, sharpens the product idea, asks every question a manufacturer needs, sends clean details, requests samples, sends shipping info, and re-sharpens the product after the sample.
- **Paperwork system** (separate graph, built later): receives paperwork, fills it from customer and shipment data, sends it back, handles extra work to get the shipment in (customs, then the local shipping company).

Customer-facing extras: pre-receipt, order tracker, stats page (money and time saved vs doing it alone, total time from order to receipt, spend), "My Products" for reordering, email and on-platform updates.

Target customers are in Saudi Arabia. Customer chat is likely Arabic and English; manufacturer chat is Chinese (WeChat later).

## 2. Ordering flow

```
select_market → pick_option (or "custom") → mandatory_questions
  → deep_dive (AI closes gaps; accepts files/photos)
  → completeness_check ──(gaps)──► back to deep_dive
  → build_pre_receipt → customer_confirm ──(changes)──► deep_dive
  → FREEZE spec (versioned)
  → translate → manufacturer step ⇄ verify loop
  → summarize_and_notify → shipping tracker
```

- Markets and options are **config**, each with mandatory questions. "Custom" has no fixed questions: the AI proposes what a manufacturer would need, asks, and records answers.
- **Completeness check is a separate LLM call with its own prompt** ("what would a manufacturer still have to ask?"). The agent that asked the questions does not grade itself.
- Photos/files go to a vision model that extracts details into spec fields; originals live in object storage and the spec holds references.
- The pre-receipt is rendered from the spec (not a price document). Once confirmed, that version is frozen.
- Quote confirmation is a separate, later document from the pre-receipt.

## 3. Spec schema (v1 draft)

```python
class FileRef(BaseModel):
    url: str
    kind: Literal["image", "document"]
    note: Optional[str] = None
    extracted: dict[str, Any] = {}

class ProductSpec(BaseModel):
    market: str
    option: str                    # option id or "custom"
    quantity: Optional[int] = None
    answers: dict[str, Any] = {}   # question id -> answer
    files: list[FileRef] = []
    open_gaps: list[str] = []
    version: int = 1
    frozen: bool = False

class Question(BaseModel):
    id: str
    prompt: str
    type: Literal["choice", "number", "text", "file"]
    choices: list[str] = []
    required: bool = True
```

Apparel needs a size-by-quantity table in the spec, not a single quantity. Device-compatibility answers (phone model, watch band width) must be confirmed explicitly.

Market registry sketch:

```python
MARKETS = {"apparel": ..., "stationery": ..., "home_textiles": ..., "tech_soft_goods": ..., "pet": ..., "packaging": ...}
def get_questions(market_id, option_id):
    m = MARKETS[market_id]
    return m["common_questions"] + m["options"][option_id]["questions"]
```

Each market also has `compliance_notes`. Saudi import rules (e.g. conformity documentation, labeling) are **unverified**; a product that may need certificates is flagged to the team instead of quoted blindly. Confirm with a customs broker.

## 4. Launch markets

| Market | Options | Key mandatory questions |
|---|---|---|
| Fashion, apparel & uniforms | hoodie, oversized tee, abaya, tote bag, corporate uniform, custom | fabric and GSM, size-by-quantity, colors (codes), print/embroidery method and placement, labels, fit reference. Abaya: length, sleeves, embellishment. Uniform: logo placement, staff count by size |
| Stationery & paper goods | daily planner, notebook, desk mat, stickers, custom | dimensions, pages, paper type/weight, binding, cover finish, print colors, Arabic RTL layout and Hijri/Gregorian dates, foil/lamination, die-cut |
| Home textiles | bed sheets, pillow covers, prayer mats, towels, custom | size, fabric and thread count/weight, colors/pattern, print or weave, hem/finish, packaging, certifications |
| Tech & lifestyle soft goods | silicone phone case, laptop sleeve, mousepad, watch band, custom | device model or band width, material, color, finish, logo method, thickness, closure |
| Pet accessories (non-food) | pet bed, leash, collar, chew toy, custom | pet size range, material, hardware, strength rating, material safety for chew toys, colors |
| Branded e-commerce packaging (B2B, Salla/Zid merchants) | tissue paper, poly mailer, corrugated box, custom | dimensions, material and thickness, print colors, closure, quantity tiers, food or fragile use |

Build the whole graph against one market first (packaging or stationery: objective specs), then add the rest as config. Apparel has the most variables, so it goes second.

## 5. Manufacturer layer

- Translate the frozen spec once; keep original wording alongside.
- **Verify loop**: every manufacturer message (quote, confirmation, counter-proposal) is compared field by field against the spec. A mismatch triggers a question back or a customer alert, never silent acceptance.
- Human approval gate for anything changing price, spec or deadlines, and for payment details.
- Summarize the conversation and send updates with photos by email and on the platform.
- Channel is an **interface** with implementations: manual relay (first), email, WeCom/WeChat. WeChat has no official API for automating a normal personal account and unofficial bots risk bans; verify the current options (WeCom is the likely official route) before committing.

### Learning how Chinese manufacturers think

Use prompts and retrieval, not fine-tuning:
1. **Playbook**: short document of how these manufacturers work (what they ask first, quote structure, MOQ, sample fees, lead times, payment terms, phrases signalling yes/maybe/no), distilled from real conversations.
2. **Example library**: annotated real exchanges split into small situations (quote request, MOQ, sample, delay, spec mismatch, quality complaint); retrieve the 3 to 5 most similar into the prompt. Postgres with `pgvector`.
3. **Per-manufacturer memory** (below).
4. **Evals**: hold back real conversations and replay them after prompt changes.

Sources: the team's own conversations, n8n test transcripts, and a **human-relay phase** where real exchanges become labeled data. Anonymize before storing (names, phones, addresses, company names, identifying prices, payment details). Check permission to use others' messages. Keep original Chinese next to translations. Label outcomes and prefer good ones. Examples guide style and questions, never what the order contains.

## 6. Memory

Every conversation starts fresh with an empty message history; relevant summaries are loaded into the prompt, and a summarizer writes back at the end.

- Store namespace `("users", user_id, "orders")`: summarized history of this customer's orders.
- Store namespace `("manufacturers", manufacturer_id, "orders")`: summarized history with this manufacturer (reliability, lead times, issues, contact style).
- The order's own state (frozen spec, stage, receipt versions) lives in the checkpointer.
- Summaries drift: keep structured facts (agreed prices, defects, dates) in tables; use summaries for softer context only.

## 7. Pricing

- Prices are pre-agreed per product type with each manufacturer and re-checked weekly to stay in range.
- **The AI never negotiates or discusses price.** It records manufacturer prices into that manufacturer's dataset (for the team to negotiate with later) and relays the quote to the customer, who confirms or waits for the sample.
- If a manufacturer raises discounts, increases, budget or quantity-for-price, or a customer asks for a lower price, the agent says the team will follow up and flags a human. Never promises.
- **Price dataset** is append-only: manufacturer, product type, key attributes, quantity and tier, unit price, currency, incoterm, date, source order or weekly check, source message and original Chinese text, status (extracted / verified / disputed).
- Customer-facing total should show product cost, Orion fee, shipping, customs and duties; store original currency and the conversion rate used.
- Stale prices (no weekly answer) block automatic quotes. Only a human changes an agreed range.
- Open: should the weekly price request be sent by a person or by a fixed agent message that only records answers (no negotiation)?
- Open: are agreed prices per quantity bracket or one price per product?

## 8. Events and timers

All triggers resume the order's thread:

| Trigger | Source |
|---|---|
| Customer message or decision | Website API |
| Manufacturer reply | Email/WeChat handler or manual relay form |
| Payment confirmed | Provider webhook |
| Shipment update | Tracking provider webhook |
| Timeout | Scheduler (see below) |

```python
def on_event(order_id, event):
    config = {"configurable": {"thread_id": order_id}}
    return app.invoke(Command(resume=event), config)
```

A `route_event` node at each wait point branches on `event["type"]`. Each trigger ends in **update** (write state/dataset) or **wait** (back to the interrupt).

Time-based things cannot be events by themselves: the 3-day manufacturer rule, quote expiry, customer abandonment, weekly price collection. When an order enters a waiting state, write `deadline_at` and the action to a table; a small periodic job finds expired rows and fires a `timeout` event into the same `on_event`. Count days on China's working calendar (weekends, long holidays like New Year). Send one reminder before escalating.

Manufacturer selection: ordered list of manufacturers per product type. Contact attempt 1 with a 3-day deadline; on no usable reply, contact attempt 2 (keep the first open since nothing is committed until the customer accepts a quote); if all exhausted, alert the team. The clock stops only on a message containing what was asked (quote or answers), not a bare "received". Once a quote is accepted, tell the others the order went elsewhere.

## 9. Payments

Customers pay Orion; Orion pays the manufacturer. Use a hosted checkout and a provider webhook (`awaiting_payment` → `paid`). Track per order what the customer paid, what Orion owes the factory, and what was paid. Pick a provider that supports the target countries and currencies. Holding customer money and paying suppliers may carry licensing, tax and accounting requirements: get professional advice before launch.

## 10. Stages

| Phase | Stage | Waiting on |
|---|---|---|
| Ordering | `draft`, `pre_receipt_review`, `spec_frozen` | Customer / automatic |
| Manufacturer | `sourcing`, `clarifying`, `quote_received` | Manufacturer / timeout / automatic |
| Customer decision | `quote_review`, `awaiting_payment`, `sample_requested`, `sample_in_transit`, `sample_review` | Customer / webhook / carrier |
| Production | `in_production`, `quality_check` (stubs routing to team) | Manufacturer / team |
| Delivery | `shipped`, `in_transit`, `customs_paperwork`, `delivered` | Tracking events / paperwork graph / customer |
| Terminal | `completed`, `cancelled`, `expired`, `refunded` | none |

Side flags (not stages): `needs_human` (with reason, from any stage), `change_requested` (to team queue). Also an `arrival_problem` stub. Customer-facing friendly status labels (Arabic and English) are needed for the tracker.

Order state fields to add: `payment_status`, `amount_paid`, `payment_reference`, `manufacturer_attempts` (manufacturer, contacted_at, deadline_at, outcome), `change_requests`, `policy_version`.

## 11. Policy flags (defaults)

```python
class Policy(BaseModel):
    payment_timing: Literal["at_quote_confirmation", "after_sample"] = "at_quote_confirmation"  # TODO(decide)
    sample_policy: Literal["stub", "free", "paid"] = "stub"                                      # TODO(decide)
    sample_paid_separately: bool = False
    post_confirmation_changes: Literal["route_to_team"] = "route_to_team"
    manufacturer_timeout_days: int = 3
    quote_validity_days: int = 7                 # TODO(decide), placeholder
    customer_response_expiry_days: int = 14      # TODO(decide), placeholder
    production_stage: Literal["stub_to_team"] = "stub_to_team"
    quality_check_stage: Literal["stub_to_team"] = "stub_to_team"
    arrival_problem_stage: Literal["stub_to_team"] = "stub_to_team"
```

Store the policy version on each order. Flags change which branch an order takes; a decision that adds new steps still needs new graph code. Later, load policy from the database so the team can edit it.

## 12. Scale and reliability

Hundreds of simultaneous orders is a small load: most orders are asleep as Postgres rows; only a few graph runs execute at once. Real limits: LLM rate limits and spend, Postgres connections, external service limits.

- Async code; API and worker as separate processes; several workers.
- Retries with backoff, a queue for non-urgent work (summaries, weekly price checks), a fallback model through OpenRouter.
- Connection pooling (PgBouncer or driver pool).
- Keep images/files in object storage, only references in state; trim history; archive checkpoints of finished orders.
- Serialize events per order (lock or queue); different orders run in parallel.
- Slow work (vision, translation, summaries) runs in the background with progress shown on the site.
- Retry and dedupe for email/WeChat sends (never send twice).
- Load test early: ~200 simulated orders with a mocked LLM to check plumbing, then a smaller real-LLM run for rate limits and cost. Set an OpenRouter spend cap and per-user rate limits.
- Audit trail: every spec version, quote and message stored.

## 13. Deployment

Hetzner VPS, Docker Compose (API, worker, Postgres, Caddy for HTTPS), API at `api.orionagentic.online`, website separate. Secrets in env vars. Hetzner snapshots plus scheduled Postgres dumps. Tracing via LangSmith free tier or Langfuse. CI/CD later (GitHub Actions). Object storage for images, quotes and PDFs (Hetzner S3-compatible). Check which Hetzner region is used, since that is where data physically sits. A hosted LangGraph platform exists but cloud regions are US/EU and self-hosted/hybrid is enterprise-only; the plan is self-hosted FastAPI first.

## 14. Risks and gaps still to design

Payment details beyond timing, post-confirmation changes policy, production updates and quality check, arrival problems and disputes, a team console for every "flag a human" moment, shipping method and incoterm, restricted/regulated products screening, intellectual property screening and terms, privacy policy, reorder shortcuts from My Products, language handling in both directions (Arabic/English customer, Chinese manufacturer), auth provider choice, email provider choice (Gmail API vs transactional service; set SPF/DKIM/DMARC), background job tooling.
