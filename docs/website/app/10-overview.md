# 10 · Overview (`/app`)

**Goal:** The landing page after sign-in. In five seconds the customer knows what needs them, what is in motion, and how they are doing.

## Sections (top to bottom)
1. **Greeting and primary action:** name, "Start a new order" button.
2. **Needs your attention** (always first; hidden when empty): confirm a quote, pay, review a sample, finish a draft, missing customs details, a team question. Each item has one button that goes straight to the right place.
3. **Active orders:** compact cards with product photo, friendly status, last update, estimated arrival.
4. **In transit:** shipments on their way with tracking status (links to Shipments).
5. **Headline stats (3 or 4 tiles):** active orders, spend this month, average order-to-delivery time, orders completed. Link to Stats. Show "savings" only once its method exists (see `16-stats.md`).
6. **Reorder shortcuts:** the last few completed products, with "Reorder".
7. **Latest updates:** the 3 newest factory updates across all orders (links to Messages).
8. **Profile completeness banner:** "2 details missing before your first shipment" (links to Business and customs profile).

## Empty states
- New account: one big card, "Start your first order", with a 3-step reminder of how it works.
- No active orders: show reorder shortcuts and the new-order button.

## Behaviour
- Updates live; no manual refresh.
- Everything listed belongs to the signed-in customer only.
- Friendly status labels must match those on the Order page.

## Data
Orders, shipments, payments, profile completeness, latest update records, stats summary.
