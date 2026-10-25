# 11 · Orders (`/app/orders`)

**Goal:** Every order in one list, with what needs attention at the top.

## Layout
- **Needs your attention** group first.
- **List (cards on mobile, table on desktop):** product photo and name, reference, market, friendly status, last update, total, estimated arrival, a colored status chip.
- **Filters:** active, delivered, closed (cancelled, expired, refunded), drafts; market; date range.
- **Search:** product name or reference.
- **Sort:** last update (default), date created, total.
- **Per-order actions:** open, continue draft, reorder (completed orders), download documents.
- **Bulk:** none for now.

## Behaviour
- Drafts expire after a set time `[TBD: expiry days]`; show a warning before they do.
- Pagination or infinite scroll once the list grows.
- Empty state: short explanation and "Start your first order".
- Status labels match the Order page.

## Data
Orders table (stage, friendly status, timestamps, totals), drafts, latest update per order.
