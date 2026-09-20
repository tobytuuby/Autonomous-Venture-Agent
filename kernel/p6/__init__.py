"""P6 synthetic portfolio, coordination, shared-service, and anomaly boundaries."""

from .anomaly import (
    AnomalyDenied,
    SyntheticAnomalyAnalyzer,
    build_analysis_request,
    compute_analysis_hash,
    compute_record_hash,
)
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
from .operations import (
    OperationsDenied,
    SyntheticOperationsKernel,
    build_operation,
    compute_evidence_hash,
    compute_operation_hash,
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
    "AnomalyDenied",
    "SyntheticAnomalyAnalyzer",
    "build_analysis_request",
    "compute_analysis_hash",
    "compute_record_hash",
    "OperationsDenied",
    "SyntheticOperationsKernel",
    "build_operation",
    "compute_evidence_hash",
    "compute_operation_hash",
]
