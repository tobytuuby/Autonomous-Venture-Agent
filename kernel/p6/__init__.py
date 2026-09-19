"""P6 synthetic portfolio identity and coordination boundaries."""

from .coordination import (
    CoordinationCollision,
    CoordinationDenied,
    SyntheticCoordinationKernel,
    build_coordination_packet,
    compute_packet_hash,
)
from .registry import (
    LIVE_FIELDS,
    IdempotencyConflict,
    P6Denied,
    SyntheticPortfolioRegistry,
    build_membership,
    build_portfolio,
    compute_configuration_fingerprint,
)

__all__ = [
    "LIVE_FIELDS",
    "IdempotencyConflict",
    "P6Denied",
    "SyntheticPortfolioRegistry",
    "build_membership",
    "build_portfolio",
    "compute_configuration_fingerprint",
    "CoordinationCollision",
    "CoordinationDenied",
    "SyntheticCoordinationKernel",
    "build_coordination_packet",
    "compute_packet_hash",
]
