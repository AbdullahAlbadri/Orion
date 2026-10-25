from typing import Any, Optional, TypedDict


class OrderState(TypedDict, total=False):
    """One order's state, saved by the checkpointer after every node.

    Values are plain JSON types so checkpoints stay readable in Postgres.
    """

    order_id: str
    stage: str                     # see docs/DESIGN.md §10
    policy_version: int
    market: Optional[str]
    spec: Optional[dict]           # ProductSpec.model_dump()
    pending: Optional[dict]        # prompt waiting on the customer; pending["step"] is the node that asked
    reply: Any                     # the customer's answer to `pending`, consumed by that node
    messages: list[dict]           # follow-up history: {"role": "customer" | "orion", "content": str}
    lang: str                      # customer's language ("ar" / "en"), sent by the website with answers
    gap_rounds: int
    pre_receipt: Optional[str]     # plain text (team, terminal, audit)
    summary: Optional[dict]        # the same, structured, in the customer's language (website receipt)
    confirmed: bool
    needs_human: Optional[str]     # latest reason the team must step in
    human_tasks: list[dict]        # every flag: {"reason", "at", ...context}
    spec_versions: list[dict]      # frozen spec history

    # Manufacturer phase
    spec_zh: Optional[dict]        # {"product_zh", "fields": [{"id", "label_zh", "value_zh"}]}
    # {"manufacturer_id", "name", "contacted_at", "deadline_at", "reminded",
    #  "outcome": waiting | clarifying | quoted | declined | no_reply | blocked}
    manufacturer_attempts: list[dict]
    current_manufacturer: Optional[str]
    event: Any                     # the event that resumed the order, consumed by handle_manufacturer_event
    processed_events: list[str]    # event ids already handled (idempotency)
    manufacturer_next: str         # "wait" | "contact_next"
    quotes: list[dict]             # {"quote_id", "manufacturer_id", "prices", ..., "expires_at", "expired"}
