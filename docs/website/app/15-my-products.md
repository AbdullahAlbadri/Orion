# 15 · My Products (`/app/products`)

**Goal:** Reorder what the customer already made without answering the questions again, and keep a record of each product's history.

## List
- Grid: photo, name, market, last ordered, last quantity, number of orders.
- Search, filter by market, archived toggle.

## Product page (`/app/products/:id`)
- Full specification, reference photos and files, notes the customer adds.
- **History:** every order of this product with date, quantity, total, landed cost per unit, delivery time, and any issues.
- Version history if the specification was edited.
- Actions:
  - **Reorder:** starts a new order pre-filled; the customer picks the quantity and confirms any changes.
  - **Edit and reorder:** changes become a new product version.
  - Archive.
  - **Margin calculator:** the customer enters the selling price; the page shows margin per unit from the last landed cost (see `16-stats.md`).

## How a product appears here
Saved after an order is approved and completed: specification, photos, files, quantities.

## Decide later
- Which steps a reorder skips (questions, sample) `[TBD]`
- Re-check the price before quoting a reorder `[recommended]`
- If the original factory is unavailable, the order follows the normal sourcing flow
- Whether the customer sees which factory made the product `[TBD]`

## Data
Products table plus the long-term memory entry used by the AI for reorders.
