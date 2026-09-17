"""Synthetic red-team payment path joining treasury authorization to P0.13.

This boundary is intentionally not a production payment gateway. It composes the
kernel-owned bootstrap treasury with the already-gated RealPaymentAdapter so the
full authorization path is executable in certification without a live provider.
The adapter remains responsible for red-team-only reachability, credentials,
instrument, beneficiary, idempotency, and exposure limits.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from integrations.payment_adapter import PaymentReceipt, RealPaymentAdapter
from .bootstrap import BootstrapTreasury, TreasuryState


class TreasuryPaymentPathDenied(PermissionError):
    """Raised when a payment cannot be authorized by the treasury path."""


@dataclass(frozen=True)
class TreasuryPaymentResult:
    allocation_id: str
    receipt: PaymentReceipt
    treasury_state: TreasuryState


class RedTeamTreasuryPaymentPath:
    """Execute the synthetic, red-team-only treasury-to-payment path."""

    def __init__(self, treasury: BootstrapTreasury, adapter: RealPaymentAdapter):
        self._treasury = treasury
        self._adapter = adapter

    def capture(
        self,
        request_id: str,
        amount: float,
        payload: dict[str, Any],
        *,
        new_venture: bool = False,
    ) -> TreasuryPaymentResult:
        if not request_id:
            raise TreasuryPaymentPathDenied("request id is required")
        allocation_id = "payment:" + request_id
        if not self._treasury.request_allocation(
            allocation_id, amount, new_venture=new_venture
        ):
            raise TreasuryPaymentPathDenied("treasury allocation was denied")

        # A failed adapter call leaves a durable pending allocation. Retrying the
        # same request is safe because both layers use the same request identity.
        receipt = self._adapter.capture(request_id, amount, payload)
        if not self._treasury.commit_allocation(allocation_id):
            raise TreasuryPaymentPathDenied("treasury commit failed")
        return TreasuryPaymentResult(
            allocation_id=allocation_id,
            receipt=receipt,
            treasury_state=self._treasury.recover(),
        )
