# 16 · Stats (`/app/stats`)

**Goal:** Show the customer where their money and time go and what Orion adds, using honest numbers they can verify.

**Principle:** every number has a "How is this calculated?" link. A number without a visible method reads as marketing.

## Layout
Date range selector (this month, 3 months, year, all time) → summary tiles → sections below → per-order table.

## 1. Spend
| Stat | Definition | Source |
|---|---|---|
| Total spend | Sum of payments in range | Payments |
| Spend by month / market / product | Grouped totals | Payments, orders |
| Average order value | Total spend ÷ orders | Payments |
| Cost breakdown | Product, Orion fee, shipping, customs per order, and in total | Quote and invoice records `[TBD: needs fee, shipping, customs rules]` |
| **Landed cost per unit** | All costs for an order ÷ units delivered | Payments, quantities |

## 2. Time
| Stat | Definition | Source |
|---|---|---|
| Order-to-delivery time | Order confirmation to delivered, average and per order | Stage timestamps |
| **Time per stage** | Specification, quote, sample, production, shipping, customs | Stage timestamps |
| Waiting on you vs waiting on the factory | Share of elapsed time in customer-owned stages vs factory-owned stages | Stage timestamps and who each stage waits on |
| Actual vs estimated delivery | Difference per order | Estimated date at quote vs delivery date `[TBD: only if estimates are made]` |

## 3. Orders and behavior
- Orders by status and by market
- Repeat and reorder rate (orders of a product already ordered ÷ orders)
- Sample-to-order rate (orders placed after a sample ÷ samples) `[after sample policy]`
- Revisions per order (spec versions after the first)

## 4. Quality
- **Mismatches caught:** factory replies the verification step found different from the frozen specification (material, quantity, color, etc.), and how each was resolved. This is the clearest evidence of Orion's value, and it comes from our own records.
- Samples approved on the first review `[after sample policy]`
- Issues reported and average time to resolve `[after dispute flow]`

## 5. Savings (only if defensible)
- **Do not show "money saved" until a baseline exists.** The baseline ("doing it yourself") needs a stated method and sources (for example typical sourcing, agent and broker costs, extra shipping steps), and must be labeled as an estimate.
- Until then, show spend, time and mismatches caught.
- Possible later: "hours of work avoided" from a method the team can explain.

## 6. Margin calculator
The customer enters a selling price per product (not stored as business data without consent `[TBD]`). The page shows margin per unit and percentage from the latest landed cost. Available from My Products and Stats.

## Empty and early states
Before the first completed order, explain which stats appear and when. Hide stats whose data does not exist yet instead of showing zeros.

## Data requirements (build in from the start)
- A timestamp at every stage change, with who the stage was waiting on. This cannot be reconstructed later.
- Per-order cost records split into product, fee, shipping, customs, with currency and rate used.
- Verification records: each mismatch, its fields and outcome.
- Quantity delivered per order.

## Availability
- **From day one:** order counts, spend, time per stage, reorder rate, mismatches caught.
- **After decisions:** cost breakdown, savings, sample stats, quality and disputes, estimated vs actual.
