# OR-0.10 Level 2B production-readiness evidence — verification record

Date: 2026-10-28 | Status: **INCOMPLETE — NOT FOR ACCEPTANCE**
Baseline: `5d42c5798c3381b6be6883c16087a1cdb32426c8`.
Approval: isolated testing approved; cutover conditionally approved only after independent Claude acceptance.

## Executed tests

```bash
infrastructure/python-runtime/.venv/bin/python -m unittest tests.test_broker_isolated_mtls tests.test_broker -q
```

Exit 0: **24 tests in 1.343 seconds, OK**. Includes 12 existing broker policy tests, 8 original TLS checks and four supplemental checks (hostname mismatch, pinset rollover logic, nonexecuting poll route, recovery after failed handshake). This is isolated loopback execution with ephemeral synthetic certificate fixtures only.

## Observed client inventory / limitations

Control `venture-control-broker.service` is running as `venture-broker` with Python HTTP server bound to TCP/8443. Control systemd unit file search for literal `8443` found none; `/usr/local/lib` Python search found only the installed broker server. Agents active service listing identifies bridge and tunnel, and no custom broker consumer. Agents Python application search for literal `8443` found none. Earlier repository search likewise found no clients beyond server. **These are negative searches, not proof of no callers:** crontabs, external monitoring, runtime traffic over time, shell scripts, untracked code, and nonliteral endpoints are not exhaustively verified. A full monitored interval and stakeholder ownership validation remain blocking.

## Scope of API

The deployed broker provides only `GET /health` and `POST /v1/capabilities/evaluate`. Ledger and finance read-only queries are not routes of this HTTP broker and should not be invented for compatibility requirements. The 12 baseline broker policy tests and the isolated TLS HTTP health/malformed-post checks are not exhaustive wire-level CAP allow/escalate/deny compatibility.

## Certificate lifecycle and cutover gaps

- Hostname mismatch and absent/untrusted client/CA checks have passed.
- The pinset test demonstrates test-side rotation logic **without active listener reload** or real issuance. It does not establish overlapping issuance, expiry enforcement, revocation/CRL, or zero-downtime migration.
- Certificate expiry using actual expired client/server certificates **not tested**.
- A full dual-listener/cutover rehearsal, runtime-client migration exercise, and secure shutdown/recovery rehearsal **not performed**.
- No OpenBao production PKI role was created; existing OpenBao availability does not prove suitable PKI permissions/roles.
- No production route/certificates/services/firewall were modified. No execution or finance authority enabled.

## Secure cutover and recovery procedure (NOT rehearsed)

1. Preflight: verify independently audited code hash and caller inventory; owner conditional authorization and Claude acceptance.
2. Record broker service, OPA, firewall and interface baselines; stage keys outside repo with narrow permissions; install dedicated mTLS identities and matching pinned trust configuration.
3. Test a protected isolated listener with both current approved API clients and Agents poll identity; verify no route can be accessed via plaintext.
4. Verify complete caller migration and production-like certificate expiration/revocation/rollover, negative peer and wire-level request cases.
5. Cutover port 8443 only after those tests; continuously check successful authenticated responses and policy denials.
6. If cutover fails, stop or isolate the broker and restore only a **secure mTLS** known-good configuration. **Never** reenable plaintext; remain unavailable until securely repaired.
7. Collect sanitized fingerprint/config/test evidence, no private keys or bearer tokens.

## Decision

This is a **partial evidence package** for subsequent execution. Independent acceptance and production cutover remain **BLOCKED** until inventory completion, actual certificate lifecycle tests, full broker HTTP regression, and a rehearsed secure cutover/rollback have passed. Do not present this report as a complete gate.
