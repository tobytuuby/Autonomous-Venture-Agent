"""Compatibility exports for P2 services; kernel remains authoritative."""
from kernel.opportunity.lifecycle import (
    HumanReviewRequired,
    LifecycleError,
    LifecycleManager,
    LifecycleScopeViolation,
    LifecycleTransitionError,
)
from kernel.opportunity.scoring import (
    ScoringError,
    ScoringPolicyMismatch,
    ScoringScopeViolation,
    ThesisScorer,
)

__all__ = [
    "HumanReviewRequired",
    "LifecycleError",
    "LifecycleManager",
    "LifecycleScopeViolation",
    "LifecycleTransitionError",
    "ScoringError",
    "ScoringPolicyMismatch",
    "ScoringScopeViolation",
    "ThesisScorer",
]
