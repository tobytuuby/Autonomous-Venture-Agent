# OR-0.10 Level 2B isolated mTLS compatibility evidence

Date: 2026-10-28. Authorization: isolated test preparation only (owner approved). Not production cutover authorization.

## Implementation
- `kernel/broker/isolated_mtls.py`: opt-in **loopback-only**, non-8443 TLS wrapper around the existing broker handler. Requires client certificate chain validation and DER SHA-256 pinning per role; no plaintext fallback; exact polling GET is non-executing. Production broker `kernel/broker/server.py`, deployed 8443 service, firewall, OpenBao and credentials untouched.
- `tests/test_broker_isolated_mtls.py`: creates ephemeral **synthetic** test CA, server and three client identities in a temporary directory. Exercises genuine local TLS handshakes (not just mocked SSL contexts).
- No production certificates were issued; synthetic test keys are temporary and never committed.

## Reproduction

```bash
infrastructure/python-runtime/.venv/bin/python -m unittest tests.test_broker_isolated_mtls tests.test_broker -q
```

Observed: `Ran 20 tests ... OK` (8 isolated mTLS tests + 12 existing policy tests). Initial test fixture failed due to a missing CA key-usage extension; fixture was corrected and all tests rerun successfully.

Covered: accepted pinned capability and poll identities, original `/health` result, malformed capability request denial, read-only polling, cross-role rejection, unpinned valid CA identity, missing client certificate, untrusted server CA, plaintext denied, method/query path restrictions and malformed pinset. Some denial semantics (e.g. wrong route may be 404 vs 403) must be frozen in a dedicated API contract before cutover.

## Limitations / remaining blocking gates

- This isolated harness does **not** upgrade the deployed broker and does not by itself establish dual-VM mTLS, trust rotation, revocation or durable signed remote execution.
- Real runtime caller inventory remains incomplete; static search only is not sufficient. Discovery of all broker callers and migration compatibility required before production activation.
- Additional tests needed: certificate expiration/rollover, explicitly wrong server hostname, revoked identity, concurrent/malformed or oversized requests, wire-level regression for capability allow/escalate/deny, client migration, private-route firewall/recovery and full production-like cutover/rollback rehearsal.
- Loopback polling fixture returns an empty synthetic assignment list; **no** manager/worker execution enabled.
- No production certificate issuance or cutover authorized by this result.

Verdict: **isolated implementation baseline PASS; OR-0.10 Level 2B operational acceptance PENDING**.
