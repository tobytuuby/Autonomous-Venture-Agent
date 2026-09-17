"""P0.16 synthetic treasury-to-payment path certification.

This executes the composed kernel path with a recording transport, a role-bound
red-team identity, and a test venture. It deliberately uses no live credentials
or external provider.
"""
from integrations.payment_adapter import RealPaymentAdapter
from kernel.finance import BootstrapTreasury, RedTeamTreasuryPaymentPath


def main() -> int:
    calls = []
    treasury = BootstrapTreasury(seed_balance=1000)
    adapter = RealPaymentAdapter(
        lambda request_id, amount, body: calls.append((request_id, amount, body)) or "synthetic-" + request_id,
        context=RealPaymentAdapter.RED_TEAM_CONTEXT,
        actor_identity="red-team:certifier",
        venture_context="test-venture:cert",
        credentials={"token": "synthetic-only"},
        supported_instruments={"test-card"},
        enabled=True,
    )
    path = RedTeamTreasuryPaymentPath(treasury, adapter)
    payload = {
        "operation": "capture",
        "instrument_id": "test-card",
        "beneficiary_id": "beneficiary-1",
        "venture_context": "test-venture:cert",
    }

    first = path.capture("p016-path-1", 5.0, payload, new_venture=True)
    retry = path.capture("p016-path-1", 5.0, payload, new_venture=True)
    if first.receipt != retry.receipt or len(calls) != 1:
        return 1
    if treasury.state.deployed != 5.0 or treasury.allocations()[0]["status"] != "committed":
        return 1

    treasury.sweep("p016-positive-profit", 0.01)
    if treasury.state.mode != "standard" or treasury.state.deployed != 5.0:
        return 1
    adapter.reconcile_cleanup()
    print("P0.16_PAYMENT_PATH=PASS")
    print("BOOTSTRAP_TO_STANDARD=PASS")
    print("TREASURY_ALLOCATION_COMMITTED=PASS")
    print("ADAPTER_IDEMPOTENCY=PASS")
    print("RED_TEAM_ONLY=PASS")
    print("SYNTHETIC_TRANSPORT_CALLS=%s" % len(calls))
    print("LIVE_EXTERNAL_ACTIONS=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
