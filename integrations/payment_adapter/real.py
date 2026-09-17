"""Gated payment boundary for P0.13 certification.

No transport is provided by default, and CEO/Venture-Manager identities are denied.
Only the explicitly marked red-team certification context can reach the injected
provider. This task never supplies live credentials or a live provider.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable

class PaymentAdapterDenied(PermissionError):
    pass

class PaymentExposureError(ValueError):
    pass

@dataclass(frozen=True)
class PaymentReceipt:
    request_id: str
    amount: float
    provider_reference: str

class RealPaymentAdapter:
    MIN_EXPOSURE = 5.0
    MAX_EXPOSURE = 20.0
    RED_TEAM_CONTEXT = "p0.13-red-team-certification"

    def __init__(
        self,
        transport: Callable[[str, float, dict[str, Any]], str] | None = None,
        *,
        context: str | None = None,
        actor_identity: str | None = None,
        venture_context: str | None = None,
        credentials: dict[str, Any] | None = None,
        supported_instruments: set[str] | frozenset[str] | None = None,
        enabled: bool = False,
    ):
        self._transport = transport
        self._context = context
        self._actor_identity = actor_identity
        self._venture_context = venture_context
        self._credentials = dict(credentials or {})
        self._supported_instruments = frozenset(supported_instruments or ())
        self._enabled = enabled
        self._exposure = 0.0
        self._receipts: dict[str, PaymentReceipt] = {}
        self._exposure_ledger: list[dict[str, Any]] = []
        self._denials: list[str] = []

    @property
    def total_exposure(self) -> float:
        return self._exposure

    @property
    def exposure_ledger(self) -> tuple[dict[str, Any], ...]:
        return tuple(self._exposure_ledger)

    @property
    def denial_log(self) -> tuple[str, ...]:
        return tuple(self._denials)

    def _deny(self, reason: str):
        self._denials.append(reason)
        raise PaymentAdapterDenied(reason)

    def _check_reachability(self) -> None:
        if not self._enabled or self._context != self.RED_TEAM_CONTEXT:
            self._deny("real adapter is red-team-only")
        if not self._actor_identity or not self._actor_identity.startswith("red-team:"):
            self._deny("CEO/Venture-Manager identities cannot reach real adapter")
        if not self._venture_context or not self._venture_context.startswith("test-venture:"):
            self._deny("test-venture context is required")
        if not self._credentials:
            self._deny("payment credentials are not configured")
        if self._transport is None:
            self._deny("real transport is not configured")

    def capture(self, request_id: str, amount: float, payload: dict[str, Any] | None = None) -> PaymentReceipt:
        self._check_reachability()
        if not request_id or amount <= 0:
            self._deny("request id and positive amount are required")
        body = dict(payload or {})
        if body.get("operation") != "capture":
            self._deny("unsupported payment operation")
        instrument = body.get("instrument_id")
        if not isinstance(instrument, str) or instrument not in self._supported_instruments:
            self._deny("unknown payment instrument")
        beneficiary = body.get("beneficiary_id")
        if not isinstance(beneficiary, str) or not beneficiary.strip():
            self._deny("ambiguous beneficiary identity")
        if body.get("venture_context") != self._venture_context:
            self._deny("venture context mismatch")
        amount = float(amount)
        if self._exposure + amount > self.MAX_EXPOSURE:
            raise PaymentExposureError("aggregate real exposure would exceed $20")
        prior = self._receipts.get(request_id)
        if prior is not None:
            if prior.amount != amount:
                raise PaymentExposureError("idempotency key reused with a different amount")
            return prior
        reference = self._transport(request_id, amount, body)
        receipt = PaymentReceipt(request_id, amount, str(reference))
        self._receipts[request_id] = receipt
        self._exposure += amount
        self._exposure_ledger.append({"request_id": request_id, "amount": amount, "provider_reference": receipt.provider_reference})
        return receipt

    def assert_certification_exposure(self) -> None:
        if self._exposure < self.MIN_EXPOSURE or self._exposure > self.MAX_EXPOSURE:
            raise PaymentExposureError("P0.13 total exposure must be between $5 and $20")

    def reconcile_cleanup(self) -> dict[str, Any]:
        self.assert_certification_exposure()
        return {"total_exposure": self._exposure, "receipt_count": len(self._receipts), "denial_count": len(self._denials), "cleaned_up": True}

    def freeze(self) -> None:
        self._enabled = False
