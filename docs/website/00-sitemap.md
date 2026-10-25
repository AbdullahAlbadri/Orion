# Orion website — sitemap

Domain: orionagentic.online (API on `api.orionagentic.online`). Arabic first (RTL), English second, mobile first. Anything marked `[TBD]` needs a team decision. Never invent prices, statistics, testimonials or timelines.

## Public (2 pages)
| Page | Route | File |
|---|---|---|
| Home (long page: how it works, markets, pricing, FAQ, about, contact) | `/` | `01-home.md` |
| Sign up / sign in + onboarding | `/start` | `02-start.md` |

## Signed-in app
| # | Page | Route | File | Priority |
|---|---|---|---|---|
| 10 | Overview | `/app` | `app/10-overview.md` | Launch |
| 11 | Orders | `/app/orders` | `app/11-orders.md` | Launch |
| 12 | New order (chat, pre-receipt, quote) | `/app/orders/new` | `app/12-new-order.md` | Launch |
| 13 | Order page | `/app/orders/:id` | `app/13-order-page.md` | Launch |
| 14 | Shipments | `/app/shipments` | `app/14-shipments.md` | Launch |
| 15 | My Products | `/app/products` | `app/15-my-products.md` | Soon after |
| 16 | Stats | `/app/stats` | `app/16-stats.md` | Soon after |
| 17 | Payments | `/app/payments` | `app/17-payments.md` | Launch (needs payment provider) |
| 18 | Documents | `/app/documents` | `app/18-documents.md` | Soon after |
| 19 | Messages and updates | `/app/messages` | `app/19-messages.md` | Launch |
| 20 | Business and customs profile | `/app/business` | `app/20-business-profile.md` | Launch |
| 21 | Help and support | `/app/help` | `app/21-help.md` | Launch |
| 22 | Settings | `/app/settings` | `app/22-settings.md` | Launch |
| 23 | Later pages | none | `app/23-later.md` | Roadmap |

Routes in the app section are suggestions; the earlier files used `/orders` and `/dashboard`.

## Navigation
- **Sidebar (7 entries):** Overview, Orders, Shipments, My Products, Payments and documents (two tabs), Stats, Settings.
- **Header:** Messages (bell with unread count), Help, language toggle, account menu.
- **Account menu:** Business and customs profile, Settings, Sign out.
- On mobile, the sidebar becomes a bottom bar with Overview, Orders, New order (center button), Shipments, More.

## Not pages
**Legal** (terms, privacy, refunds, restricted products, IP) is one drawer opened from the footer, the sign-up checkbox and Settings. A lawyer must review it before launch.

## Rules for every page
- Friendly status labels are the same everywhere (defined in `app/13-order-page.md`).
- A customer can only see their own data.
- The AI never discusses or negotiates price, and never changes addresses or payment details on its own.
- Anything customer-facing about customs, labeling or certification needs a customs broker's verification before publishing.

## Archive
`archive/` holds the first 20-page version and the earlier tabbed dashboard.
