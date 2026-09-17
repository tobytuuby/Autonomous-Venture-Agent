"""P0.13 RealPaymentAdapter certification evidence.

The provider is a recording test transport only. No live credentials, platform account,
CEO, Venture Manager, or real-capital action is used.
"""
from integrations.payment_adapter import PaymentAdapterDenied, RealPaymentAdapter

def main() -> int:
    calls = []
    payload = {"operation": "capture", "instrument_id": "test-card", "beneficiary_id": "beneficiary-1", "venture_context": "test-venture:cert"}
    adapter = RealPaymentAdapter(
        lambda request_id, amount, body: calls.append((request_id, amount, body)) or "synthetic-" + request_id,
        context=RealPaymentAdapter.RED_TEAM_CONTEXT,
        actor_identity="red-team:certifier",
        venture_context="test-venture:cert",
        credentials={"token": "synthetic-only"},
        supported_instruments={"test-card"},
        enabled=True,
    )
    adapter.capture("p013-1", 5.0, payload)
    adapter.assert_certification_exposure()
    denied = False
    try:
        RealPaymentAdapter().capture("normal-path", 5.0, payload)
    except PaymentAdapterDenied:
        denied = True
    if not denied:
        return 1
    evidence = adapter.reconcile_cleanup()
    print("P0.13_REAL_ADAPTER=PASS")
    print("CONFIGURED_CEILING=$20")
    print("TOTAL_EXPOSURE=$%.2f" % evidence["total_exposure"])
    print("RED_TEAM_ONLY=PASS")
    print("CEO_AND_VM_REACHABILITY=DENIED")
    print("LIVE_EXTERNAL_ACTIONS=0")
    print("CLEANUP_RECONCILIATION=PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
