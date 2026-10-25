# 17 · Payments (`/app/payments`)

**Goal:** Show every payment clearly. Money pages are where trust is won or lost.

## Sections
- **Summary:** paid this month, total paid, amount due now, refunds pending.
- **Due now:** orders waiting for payment, with the amount, what it covers, validity of the quote, and a **Pay** button that opens the hosted checkout. The AI never sees or handles payment details.
- **History table:** date, order, description, amount, currency, method, status (paid, pending, failed, refunded), receipt download.
- **Order payment detail:** deposit and balance if the payment is split `[TBD: payment timing and structure]`, the cost breakdown, and the exchange rate used.
- **Refunds:** requested, approved, paid, with dates `[TBD: refund policy]`.

## Behaviour
- Payments are confirmed by the payment provider's webhook, never by the browser alone.
- Failed payment: clear message and a retry button.
- Receipts and invoices are generated for every payment and stored in Documents.
- Currency shown in the customer's currency, with the original currency and rate where relevant `[TBD: currencies]`.

## Do not
Store or display card numbers. Show only provider references and the last four digits if the provider supplies them.

## Needs
Payment provider `[TBD]`, payment timing and refund policy `[TBD]`, licensing and accounting advice on holding customer funds and paying suppliers.
