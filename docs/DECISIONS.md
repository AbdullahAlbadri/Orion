# Decisions

Search the code for `TODO(decide)` to find every open flag.

## Decided by the team

| Topic | Decision |
|---|---|
| Orchestration | LangGraph (chosen mainly for built-in per-order memory/checkpointing) |
| LLM access | OpenRouter |
| Server / domain | Hetzner, orionagentic.online |
| Launch markets | Fashion/apparel/uniforms, stationery & paper goods, home textiles, tech & lifestyle soft goods, pet accessories (non-food), branded e-commerce packaging (B2B) |
| Price handling | Prices pre-agreed per product type, re-checked weekly; AI never discusses or negotiates price, only records manufacturer prices into each manufacturer's dataset and relays quotes |
| Payments | Customers pay Orion; Orion deals with the manufacturer |
| Manufacturer timeout | If no response in 3 days, contact another manufacturer |
| Memory | Two summarized memories (per-user orders, per-manufacturer orders); every conversation starts fresh and uses them |
| Triggers | Manufacturer or customer events update the dataset or wait for a response |
| Manufacturer learning | Feed real Chinese-manufacturer conversations to the manufacturer agent |
| Repos | New backend repo; old n8n/landing-page repo stays separate as reference |
| First test market | Fashion & apparel (build the full graph against it, then add other markets as config) |
| Auth | Own JWT (no third-party auth provider). Customers sign in with email (one-time code or link) or Google / Apple; no passwords |
| Team console | Simple internal page built with the API (team login only) |
| Customer ordering screens | Built in this project alongside the API |

## Default flags (can be changed later)

| Flag | Default | Notes |
|---|---|---|
| `payment_timing` | `at_quote_confirmation` | Alternative: `after_sample`. Affects stage order |
| `sample_policy` | `stub` | Customer can choose "wait for sample"; routes to team until policy exists |
| `sample_paid_separately` | `False` | Placeholder |
| `post_confirmation_changes` | `route_to_team` | Team will discuss policy |
| `quote_validity_days` | `7` | Placeholder, not decided |
| `customer_response_expiry_days` | `14` | Placeholder, not decided |
| `ai_question_rounds` | `2` | First round asks everything at once; the second only follows up on answers; then open gaps go to the team |
| production / quality check / arrival problem | stub to team | Not designed yet |

## Open questions

- Price dataset shape: per quantity bracket, or one price per product?
- Weekly price collection: sent by a person, or a fixed agent message that only records answers?
- Email approach (Gmail API vs transactional service plus inbox)
- WeChat route (WeCom vs human relay first); verify current options
- Payment provider, and licensing/tax/accounting advice
- Customs/SASO requirements per product category (ask a customs broker)
- Sample policy
- Post-confirmation changes policy
- Production, quality check, arrival-problem and dispute handling
- Customer-facing status labels (Arabic and English)
- Expected volume (orders per month, messages per order) to size LLM limits
- Whether any customer or order data in the old system needs migrating
