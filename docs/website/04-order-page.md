# 4 · Order page (`/orders/:id`)

**Goal:** The most-used page. One place to see where the order is, what happened, and what to do next.

## Layout
1. **Header:** reference, product name and photo, current friendly status, and a **"What's needed from you"** banner when the customer must act (confirm quote, pay, review sample).
2. **Timeline** (friendly labels, not internal stages; `[TBD: team wording, Arabic and English]`):
   Preparing your order → We're working with the factory → Your quote is ready → Waiting for payment → Your sample → In production → On its way → Customs paperwork → Delivered. Closed states: cancelled, expired, refunded.
3. **Updates feed:** AI-written summaries of factory conversations with photos, newest first, marked if also emailed.
4. **Sections or tabs:**
   - **Details:** pre-receipt versions, quote, total
   - **Files:** artwork, factory photos, documents for this order
   - **Shipment:** carrier, tracking number, status history, estimated arrival; updates by email too
   - **Payments:** amount paid, status
   - **Sample:** how it works, the review checklist (dimensions, material, colors, print placement, labels, Arabic text direction), approve or request changes `[TBD: sample policy]`
   - **Chat with the assistant:** resume the order conversation, e.g. after a sample arrives
5. **Actions:** confirm quote, pay, approve sample or request changes, request a change (to the team `[TBD: change policy]`), report a problem `[TBD: dispute flow]`, talk to the team, download documents.

## Behaviour
Live updates without refresh. A customer can open only their own orders. Show the factory-waiting state honestly; mention the 3-day rule only if the team keeps that promise.
