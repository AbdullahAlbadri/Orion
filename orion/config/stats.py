"""Assumptions behind the customer's "time saved" estimate. Shown to customers as an estimate.

TODO(decide): the team confirms these from real experience of sourcing without Orion.
"""

HOURS_PER_SPEC = 2.0        # writing a factory-ready spec and translating it into Chinese
HOURS_PER_FACTORY = 1.5     # finding, vetting and first contact with one factory
HOURS_PER_MESSAGE = 0.25    # writing or translating one factory message (and waiting across time zones)

# TODO(decide): money saved needs a baseline price (e.g. a typical sourcing-agent fee, or the customer's own
# reference price) and the order value from the customer quote. Until then it is not shown as a number.
