# Genuine P0.15 pre-model adversarial gate

Run the no-model harness with:

    PYTHONPATH=. python3 -m tests.certification.pre_model_certify

The harness defines exactly ADV-001 through ADV-049 and runs only kernel controls
against role-bound red-team identities. It produces per-ID evidence. It writes a
valid pre-model gate only when the derived result is 49 PASS, 0 FAIL, and 0
PENDING. Otherwise it removes the requested gate path, writes only a report, and
exits nonzero.

The current implementation executes 12 scenarios:
ADV-003, ADV-004, ADV-005, ADV-006, ADV-007, ADV-010, ADV-013, ADV-014,
ADV-015, ADV-018, ADV-019, and ADV-022. The remaining 37 scenarios are
explicitly PENDING until their controls are implemented and independently
tested. This is expected partial progress, not certification.

The harness imports no CEO agent, model provider, browser, shell, or file tools.
