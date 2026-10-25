# 20 · Business and customs profile (`/app/business`)

**Goal:** Keep, in one place, the information the paperwork system needs, and show clearly what is missing before it blocks a shipment.

## Sections
- **Completeness checklist (top):** a progress bar and a list such as "Tax number: missing, needed before first shipment". Each item has a button to fix it. Items are grouped by when they are needed: before the first order, before the first shipment.
- **Business details:** name, type, registration details, store link (Salla, Zid, other), description of what the business sells (the AI reads this before each order) `[TBD: exact fields from the real forms]`.
- **Addresses:** shipping and delivery addresses, default address, contact person and phone, delivery notes.
- **Customs details:** the fields the customs forms need `[TBD: exact list from the real customs forms]`, with a short reason beside each ("used to fill your customs paperwork").
- **Authorized contacts:** who can sign or receive.

## Behaviour
- Changes to addresses or customs details on a live order need confirmation and notify the team; the AI never changes them alone.
- Show which orders a change affects.
- Sensitive identifiers: masked in the UI, minimal access, not sent to the AI model unless strictly needed `[TBD: security and legal review]`.
- Validate formats in the browser and on the server.

## Data
Business profile and address tables, and the long-term "business profile" memory used by the AI.
