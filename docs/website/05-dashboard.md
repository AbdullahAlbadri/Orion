# 5 · Dashboard (`/dashboard`)

**Goal:** Everything about the account in one page, with tabs. Opens on Orders.

## Tab: Orders
- **Needs your attention** first (confirm quote, pay, review sample, unfinished drafts).
- Cards: photo, name, reference, friendly status, last update, total, estimated arrival. Filters (active, delivered, closed, drafts), search, sort by last update. Drafts expire `[TBD: days]`, with a warning.
- Empty state: "Start your first order". Friendly labels match page 4.

## Tab: My Products
- Saved after an order is approved and completed: specification, photos, files, past quantities.
- **Reorder** (pre-filled, customer picks quantity) and **Edit and reorder** (changed version saved as a new product version). Archive.
- `[TBD: which steps a reorder skips; re-check price before quoting (recommended)]`.

## Tab: Stats
- Spend, order count, time from order to delivery. **Money saved** only with a defensible baseline and a "How is this calculated?" link `[TBD: method]`; otherwise show spend and time only.
- Tiles, then charts, then a per-order table; date range. Empty state before the first completed order.

## Tab: Documents
- Pre-receipts (each version), quotes, invoices, receipts, shipping and customs paperwork, sample records. Filter by order and type, preview, download. Show missing customer fields for paperwork with a link to fix them. Keep every version; signed, expiring links.

## Tab: Settings
- Profile, business, addresses, customs details, language and date format (Hijri/Gregorian), notifications per event, privacy (download or delete data `[TBD]`), security (sessions). Changes to an address or customs details on a live order need confirmation; the AI never changes them alone.
