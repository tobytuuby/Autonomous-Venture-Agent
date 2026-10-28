# OR-0.10 Level 2B — Production readiness review package

Date: 2026-10-28. Baseline: `e89a023cc12778f114e3751465ddfbef45aced49`.
**Decision: READY FOR INDEPENDENT REVIEW OF ISOLATED TESTS; NOT CERTIFIED FOR CUTOVER.**
Owner pre-authorized conditional cutover only after complete readiness verification and independent Claude acceptance. No live execution authorized.

## 1. Actual API surface and client inventory

- **Control:** `venture-control-broker.service` active. Existing Python broker service exclusively exposes `GET /health` and `POST /v1/capabilities/evaluate` on `0.0.0.0:8443` as plaintext HTTP; service account `venture-broker`.
- **Agents:** running service inventory contains bridge/tunnel and OS services; no identified custom consumer of broker.
- **Control searches:** repository tracked Python/service references, `/etc/systemd/system`, `/usr/local/bin`, `/etc/cron.d`, `/etc/crontab` for literal `8443` or `capabilities/evaluate`; no additional match reported. `/usr/local/lib` Python scan matched only the installed broker handler.
- **Agents searches:** application Python files plus the same systemd, bin and cron locations; no caller references reported.
- **Connection snapshot:** Control's `ss -tn '( sport = :8443 or dport = :8443 )'` showed no established connections at time of inspection.
- **Migration matrix:** Existing broker server (not client): replace its TCP transport with mTLS. Capability HTTP clients: none found in searched scopes; unknown intermittent/untracked external consumers **cannot be excluded**. Polling client: new protocol in Agents workspace, not activated; configure client certificate and server CA/SAN after policy gate. Monitoring: no explicit 8443 monitoring client found; any unlocated monitors require discovery and migration before cutover.
- **Financial/ledger endpoints:** not served by the current broker; there is no basis to invent migration tests for them.

**Inventory limitation:** Passive one-time connection checks and text searches cannot prove an exhaustive external-caller inventory. Require a bounded observation window and actual caller-owner attestation or explicit waiver at independent review. This is a blocking residual uncertainty, not silently certified as complete.

## 2. Reproducible isolated test evidence

```bash
infrastructure/python-runtime/.venv/bin/python -m unittest tests.test_broker_isolated_mtls tests.test_broker -q
```

Observed exit code **0**: `Ran 27 tests in 3.645s; OK`. 12 existing policy tests and 15 isolated mTLS HTTP/certificate tests. No production certificate, restart, port change, firewall change, assignment or funds.

Positive: real loopback TLS connections with authorized capability/poll clients, original health JSON, capability `deny` and `escalate` wire responses under mTLS, malformed POST 400, empty nonexecuting polling.

Negative: missing/unpinned identity, CA mismatch, plaintext, hostname mismatch, route/method/role isolation. Certificate lifecycle uses real CA-signed expired client fixture (TLS rejects), real CA-signed replacement identity (denied before enrollment), overlapping old/new pinset accepts both, retired old pin denied. This is a test-only **restarted listener rollover**, not production live reload. Pin withdrawal implements local certificate pin revocation; it is **not** a CRL/OCSP validation test.

Recovery rehearsal: authenticated isolated listener serves health, shuts down, plaintext HTTP to shut-down port fails, new authenticated isolated listener serves health. This establishes **secure fail-closed restoration in isolation**; does not demonstrate zero-downtime migration or operational systemd cutover.

## 3. Production cutover runbook — NOT EXECUTED

1. Snapshot service source/unit hashes, policy, firewall, ingress and nonsecret OpenBao configuration; finish client-owner inventory and independent acceptance.
2. Verify CA capability, certificate issuance policy and service account read permissions; provision distinct short-lived broker server and Agents client identities out-of-tree. Never commit keys or tokens.
3. Deploy verified mTLS server package to isolated nonproduction listener; pin production identities; run positive/negative role, path, hostname, expiry, and revocation checks.
4. Migrate every verified client to trusted HTTPS and client certificate before cutover; no plaintext broker client may remain. **If caller inventory cannot be closed, do not cut over.**
5. Cut over only with the conditionally approved configuration and operator backout plan; confirm 8443 no longer serves plaintext; test `/health` and capability decisions from authorized client and reject all other identities.
6. Keep polling nonexecuting until separate Level 2C review; do not enable worker, owner, capital or finance authority.
7. On failure: stop/isolate broker, retain firewall restrictions, and restore only verified **mTLS** configuration; if unavailable remain down. Never restore the plaintext implementation.
8. Preserve sanitized certificate public fingerprints, commands, result counts, service logs, policy and config checksums and reviewer decision.

## 4. Independent acceptance blockers

- Runtime-client exhaustive confirmation remains outstanding (external, intermittent or nonliteral consumers); owner or independent auditor must resolve explicitly.
- Actual OpenBao PKI role/provisioning and rotation not rehearsed; production certificates remain unauthorized until the readiness gate completes.
- Production-like systemd unit/cutover and real shared TCP/8443 staging not rehearsed; no zero-downtime guarantee.
- CRL/OCSP not implemented; pin withdrawal prevents identity reacceptance when the listener is reconfigured. A stronger revocation policy must be agreed if required.
- The isolated wrapper currently allows only an explicitly supplied empty/nonexecuting pending callback; it does not constitute hardened operational routing or 2VM authentication.

**Conclusion: expanded isolation tests PASS; full production readiness package still has material unverified gates. Claude should review findings, but MUST NOT issue an unqualified readiness ACCEPTED verdict without closing those gates.**
