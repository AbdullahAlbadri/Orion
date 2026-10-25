# 14 · Shipments (`/app/shipments`)

**Goal:** One place to see everything that is on its way, since customers check this constantly.

## List
- Tabs: **In transit**, **Delivered**, **All**.
- Row: order and product, carrier, tracking number (copy button), current status, last location or event, estimated arrival, delay flag.
- Sort by estimated arrival.

## Shipment detail (opens from a row, or from the Order page)
- Status timeline: shipped from factory, in transit, arrived in the country, customs, local carrier, delivered `[TBD: statuses available from the tracking provider]`.
- Carrier, tracking number, link to the carrier's tracking page.
- Delivery address and contact (changing an address on a live shipment requires confirmation and goes to the team; the AI never changes it alone).
- **Customs paperwork status:** waiting for details, being prepared, sent to the shipping company, cleared `[TBD: depends on paperwork system]`. Shows exactly which customer field is missing if one is.
- Packing and shipping documents.
- Report a problem (delay, damage, missing items) `[TBD: dispute flow]`.

## Notifications
Email and in-app on shipped, arrived in country, customs update, out for delivery, delivered, delay.

## Data
Shipment records fed by tracking-provider webhooks `[TBD: provider]`, customs paperwork status, address.

## Do not
Promise delivery dates. Show the carrier's estimate, labeled as an estimate.
