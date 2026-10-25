"""How a customer price is made from a manufacturer's price. Code only: the AI never sets or discusses prices.

customer unit price = factory unit price x (1 + fee) x rate to SAR
shipping            = the factory's shipping price x rate to SAR (approximate, no fee)
The customer sees the prices, never the fee or the factory's own figures.
"""

from pydantic import BaseModel


class Pricing(BaseModel):
    fee_rate: float = 0.05                   # Orion's fee, added to product and sample prices (decided)
    # Fixed rates to SAR, updated by the team. SAR is pegged to USD at 3.75. CNY: SAMA's published rate was
    # about 0.555 in mid-2026 (checked 2026-10-25); rounded down here.
    to_sar: dict[str, float] = {"SAR": 1.0, "USD": 3.75, "CNY": 0.55}
    rates_checked: str = "2026-10-25"


PRICING = Pricing()
