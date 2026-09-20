"""P6 synthetic portfolio, coordination, and shared-service boundaries."""

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
from .shared_service import (
    DemandDenied,
    SyntheticSharedServiceRunner,
    build_demand,
    compute_demand_hash,
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
    "DemandDenied",
    "SyntheticSharedServiceRunner",
    "build_demand",
    "compute_demand_hash",
]
