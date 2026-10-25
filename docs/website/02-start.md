# 2 · Sign up / sign in + onboarding (`/start`)

**Goal:** Create the account and collect once everything later stages need (especially customs paperwork) without making it feel heavy.

## Flow
1. **Sign up / sign in** (toggle): name, email, phone, password or provider sign-in `[TBD: auth provider]`; checkbox to accept terms and privacy (opens the Legal drawer); email verification; language.
2. **Your business:** name, type, store link (Salla, Zid, other), one or two lines on what you sell (feeds the AI's knowledge of the business).
3. **Shipping address:** warehouse or delivery address, contact person, phone, notes.
4. **Customs details:** the fields the paperwork system will need `[TBD: exact list from the real customs forms]`. Explain why each is asked. Mark what is needed before the first order vs before the first shipment.
5. **Preferences:** notifications (email), language, currency display.
6. **Done:** "Start your first order" → `/orders/new`.

## Behaviour
- Progress bar; "finish later" allowed except what the first order needs.
- Validate on the browser and the server.
- Sensitive IDs: minimal access, masked in the UI, not sent to the AI unless strictly needed `[TBD: security/legal review]`.
- Saves to the business profile that the AI reads at the start of every order.
