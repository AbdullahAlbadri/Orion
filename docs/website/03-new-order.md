# 3 · New order (`/orders/new`)

**Goal:** Turn the idea into a complete, frozen specification, then show the quote. One page, three steps.

## Step A: Guided chat
- **Layout:** chat on the main area; a live **spec panel** beside it (bottom sheet on mobile) showing captured fields ("Material: Kraft · Size: 20 × 15 × 8 cm · Quantity: 500"). Tap a field to correct it; missing fields are highlighted.
- **Flow:** choose a market → choose an option or "Something else" → mandatory questions (buttons, numbers, uploads) → AI follow-ups to close gaps → files and photos read by the AI and added to the panel → a separate completeness check ("what would a manufacturer still have to ask?"), looping back if gaps remain.
- **Behaviour:** autosave drafts and resume; show existing drafts first; Arabic or English input with one consistent spec; the AI never discusses price (it says the team handles that); if the AI is down, keep the form fields usable.

## Step B: Pre-receipt (specification, no price)
- Order reference, version, market, option, full specification in sections, uploaded files with notes, anything "to be confirmed with the factory".
- **Confirm** (freezes the specification; say so before the button) or **Edit** (back to the chat). Download PDF. Changes after confirming create a new version `[TBD: change policy]`.

## Step C: Quote (appears later, when the factory has replied)
- Tied to the frozen version. Breakdown: product cost, Orion fee, shipping, customs `[TBD]`; quantity, unit price, total, currency and rate used; validity date `[TBD]`; estimated time only from real data.
- Actions: **Confirm order** → payment `[TBD: payment timing]`; **Wait for a sample** `[TBD: sample policy]`; **Ask the team**; **Request a lower price or change** → goes to the team, nothing promised.
- The customer is notified by email when the quote is ready; Step C is then opened from the Order page (page 4).

## Backend notes
Prices are extracted by the AI but validated by code against the quoted text; ambiguous or out-of-range prices go to the team first. Market and option config comes from the backend; uploads go to object storage with size and type limits.
