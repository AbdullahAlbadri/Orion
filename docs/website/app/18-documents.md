# 18 · Documents (`/app/documents`)

**Goal:** All paperwork for all orders in one searchable place.

## Document types
- Pre-receipts (every version)
- Quotes
- Invoices and payment receipts
- Sample records and photos
- Packing and shipping documents
- Customs paperwork filled by the paperwork system
- Factory photos and quality-check reports `[TBD: stage not designed yet]`
- Files the customer uploaded (artwork, references), clearly separated from Orion-generated documents

## Features
- Filter by order, type, date; search by name.
- Preview in the browser, download as PDF.
- Paperwork status: draft, needs your review, sent to the shipping company.
- If a form needs a customer detail that is missing, show the exact field and a link to complete it (Business and customs profile).
- Every version kept; nothing overwritten.

## Behaviour
- Access only to the customer's own documents; signed, expiring download links.
- Retention rules `[TBD: legal and accounting requirements]`.

## Shared sidebar entry
Payments and Documents share one sidebar entry ("Payments and documents") with two tabs.
