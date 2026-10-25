"""Open business decisions as flags with defaults. Search for TODO(decide) to find them."""

from typing import Literal

from pydantic import BaseModel

POLICY_VERSION = 1


class Policy(BaseModel):
    payment_timing: Literal["at_quote_confirmation", "after_sample"] = "at_quote_confirmation"  # TODO(decide)
    sample_policy: Literal["stub", "free", "paid"] = "stub"                                      # TODO(decide)
    sample_paid_separately: bool = False
    post_confirmation_changes: Literal["route_to_team"] = "route_to_team"
    manufacturer_timeout_days: int = 3           # China working days
    manufacturer_reminder_days: int = 1          # TODO(decide): working days after the one reminder before moving on
    quote_validity_days: int = 7                 # TODO(decide), placeholder
    customer_response_expiry_days: int = 14      # TODO(decide), placeholder
    production_stage: Literal["stub_to_team"] = "stub_to_team"
    quality_check_stage: Literal["stub_to_team"] = "stub_to_team"
    arrival_problem_stage: Literal["stub_to_team"] = "stub_to_team"
    # Completeness checks that still find gaps before we show the pre-receipt anyway and flag a human.
    max_gap_rounds: int = 4                      # TODO(decide), placeholder
    # The AI's follow-up choices show a relative $ / $$ / $$$ like the form's (its own estimate, never an amount).
    ai_cost_tiers: bool = True                   # TODO(decide): or only tiers the team set in config
