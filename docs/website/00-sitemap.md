# Orion website — 5 pages

Domain: orionagentic.online (API on `api.orionagentic.online`). Arabic first (RTL), English second, mobile first. Anything marked `[TBD]` needs a team decision. Never invent prices, statistics, testimonials or timelines.

| # | Page | Route | Who | File |
|---|---|---|---|---|
| 1 | Home (one long page) | `/` | Visitors | `01-home.md` |
| 2 | Sign up / sign in + onboarding | `/start` | New users | `02-start.md` |
| 3 | New order (chat, pre-receipt, quote) | `/orders/new` | Signed in | `03-new-order.md` |
| 4 | Order page (timeline, updates, tracker, files) | `/orders/:id` | Signed in | `04-order-page.md` |
| 5 | Dashboard (tabs: Orders, My Products, Stats, Documents, Settings) | `/dashboard` | Signed in | `05-dashboard.md` |

## Not pages (on purpose)
- **Legal** (terms, privacy, refunds, restricted products, IP): one scrollable drawer opened from the footer and from the sign-up checkbox. Required before taking payments; have a lawyer review it.
- **Guides, samples, pricing, FAQ, about, contact:** sections on the Home page, or later pages once there is traffic and real content.

## What was merged where
| Old page | Now lives in |
|---|---|
| How it works, Markets, Pricing, FAQ, About/trust, Contact | Home sections |
| Sign-up, Onboarding | Page 2 |
| Pre-receipt, Quote review | Page 3 (steps after the chat) |
| My orders, My Products, Stats, Documents, Settings | Page 5 (tabs) |
| Samples | Page 4 (sample step) until the policy exists |
| Guides | Later |

The previous 20 files are in `archive/`.
