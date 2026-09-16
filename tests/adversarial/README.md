# Genuine P0.15 pre-model adversarial gate

Run the no-model harness with:

    PYTHONPATH=. python3 -m tests.certification.pre_model_certify

The harness defines exactly ADV-001 through ADV-049 and attempts every case on
every run against role-bound red-team identities. It produces per-ID evidence.
It writes a valid pre-model gate only when the derived result is 49 PASS, 0 FAIL,
and 0 PENDING. Otherwise it removes the requested gate path, writes only a
report, and exits nonzero.

The current implementation passes 32 scenarios and explicitly fails 17 because
their faithful kernel controls are not implemented yet. No case is skipped or
marked PENDING. This is expected partial progress, not certification.

The harness imports no CEO agent, model provider, browser, shell, or file tools.
