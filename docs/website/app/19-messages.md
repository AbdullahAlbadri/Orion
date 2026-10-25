# 19 · Messages and updates (`/app/messages`)

**Goal:** One inbox for everything Orion tells the customer, across all orders, so nothing is buried in individual order pages or emails.

## Contents
- **Factory updates:** AI-written summaries of conversations with manufacturers, with photos.
- **Status notifications:** quote ready, payment received, sample update, shipped, delivered, delay, problem.
- **Team messages:** replies from the Orion team to support requests, price or change requests, and flagged items.
- **Action requests:** items that need the customer, with a button.

## Layout
- Left: list grouped by order, unread count, filters (all, needs action, by order, updates, team).
- Right: the selected message with photos and files, and a link to the order.
- Header bell icon shows unread and opens a small preview.

## Behaviour
- Every message that was also emailed is marked as such.
- Read/unread state; mark all as read.
- Customer can reply to team messages here; replies go to the team queue.
- The AI assistant chat for an order stays on the Order page. This inbox is for notices and team conversations.

## Data
Notification records created whenever an order event produces a customer-facing update.
