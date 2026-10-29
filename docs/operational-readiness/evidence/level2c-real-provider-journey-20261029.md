# Level 2C — real two-VM AI CEO/Manager operational journey

**Observed UTC:** October 29, 2026, 06:13–06:16 UTC.
**Result:** Complete two-round provider-backed **PREPARATION_ONLY** exchange; evidence delivered for independent Claude acceptance, which is **not claimed here**. No production authorization was issued.

## Authoritative code and installation

- Main repository code tested, committed and pushed through `b0aa505`. Changes after original `edf3a0f` baseline: `3fbff16` (CEO-pinned signed task ingress and status), `06b8139` (Control-side centralized inference executor for Manager), `58b9e43` (CEO provider-binding correction), and `b0aa505` (GPT-6 `max_completion_tokens` compatibility). The earlier snapshot `8d56164` records separate receipt-only evidence; it is superseded for operational status by this report, but remains a historical record.
- Production-like bounded Control broker: `venture-control-broker-mtls.service`, running on existing private firewall-restricted port 8443, backed by isolated `/usr/local/lib/venture-control-broker-level2c` and Control-only `resources.sqlite` plus `outbox.sqlite`.
- Dedicated Control CEO: `venture-level2c-ceo.service`, `venture-ceo` OS identity, private Ed25519 seed and private state, direct Control-side API credential, central reservation over separately pinned CEO mTLS identity.
- Dedicated Agents Manager: `venture-level2c-manager.service`, `venture-manager` OS identity, separate Ed25519 seed and private state. **No provider API credential on Agents.** Manager inference is reserved with and executed through the Control mTLS broker, against the central ledger and Control-held provider credential.
- Central standing policy: `maximum_requests=8` per bounded session and `maximum_output_tokens=512` per request; Control-side daily quota remains independently enforced. No automatic retry of ambiguous paid calls, no separate Agent-local inference ledger.
- Dedicated signed assignment submission endpoint accessible only to pinned CEO mTLS cert, signed receipt route and polling accessible only to pinned Manager identity, and CEO-only status endpoint. Dedicated CEO OpenBao clientAuth cert expires **2026-11-12 05:40:59 UTC**; original Agents client cert expires **2026-11-11 ~16:54 UTC**. Rotate both before expiry.

## Real provider-backed session

Session: `level2c-live3-20261029`. Venture identifier: `venture-verification`, explicitly bounded to preparation-only technical validation; **not an approved launch or customer-facing operation**.

Persistent Control CEO log state changes, in order:

```text
WAITING_ACK
WAITING_ACK
COMPLETE_RECEIPTS_ONLY
```

CEO provider trace: **2 PASS** responses, reported provider model `gpt-6-sol`, JSON schema validation passed. Control broker Manager provider trace: **2 PASS** `gpt-6-sol` responses. Agents Manager state: **2 completed inference calls and 2 signed acknowledgements sent**. Control central `remote_executions` has **2 COMPLETE**, CEO durable state has **2 completed calls**. The success path was performed by concurrently running services; no ChatGPT relay, per-call operator approvals, or synthetic inference fixture was involved.

Both signed outbox assignments were independently verified against the operator-owned Ed25519 trust records, and the respective Manager acknowledgements independently verified against their matching signed assignments:

| Task | CEO issuance (UTC) | Manager ACK (UTC) | Broker state | Verified receipt |
|---|---|---|---|---|
| `level2c-live3-20261029-1` | 2026-10-29T06:13:17.473345+00:00 | 2026-10-29T06:13:22.320627+00:00 | ACKNOWLEDGED | RECEIVED |
| `level2c-live3-20261029-2` | 2026-10-29T06:13:26.228103+00:00 | 2026-10-29T06:13:30.725155+00:00 | ACKNOWLEDGED | RECEIVED |

The assignments had exactly **300 seconds validity** (5 minutes), with one-shot nonces and signed body correlation, and the Manager receipts were signed with the separate Manager identity.

Canonical signed JSON SHA-256 (no secrets included):

| Task | Signed assignment SHA-256 | Signed Manager ACK SHA-256 |
|---|---|---|
| round 1 | `44b56c61478e6fcf05836d7aaabc384105ff274e443e8d55996fd8695f22e849` | `28c199730e3741e21f2020b2fdf9b3ebb4323873c0ae0836ae1311dc1283d45d` |
| round 2 | `a86202a16a970126ec31097bea7c634fb41f0dfc32ad1a2c470a01f983c219b4` | `1f0ef8c1438a71a716b25a0d9c8f12b894abbbf35a26345b4456bed3daf304c1` |

At 2026-10-29T06:15:53Z Control ledger reported **4 reserved in this successful session**, **8 historical reservations total** (including earlier smoke, aborted and failed requests; do not equate all eight with invoiced model calls), **2 completed Manager broker executions**, **2 CEO completed calls**. At 2026-10-29T06:15:55Z Agents Manager database reported **2 completed calls and 2 ACK sent**.

## Live role separation, failures and recovery

- Real Agents pinned mTLS identity: Manager `GET /v1/assignments/pending` HTTP **200**; same identity accessing CEO-only status HTTP **403**.
- Real CEO pinned mTLS identity: Manager-only polling HTTP **403**.
- Signing verification: signatures independently validated by `verify_assignment` and `verify_acknowledgement`; modified assignments, nonce replay, role mismatch, central budget exhaustion, network failures, and tampering are covered by isolated negative tests. These negatives were **not all retested against live production services**.
- Broker and Manager systemd services were restarted after completion. CEO systemd service restarted and returned `COMPLETE_RECEIPTS_ONLY` then exited successfully (a bounded finite CEO session, not continuously operating platform CEO). Broker remained active, Manager remained active and polled successfully, with both signed receipts present.
- Following restarts Control still had **8 total quota reservations, 4 session calls, 2 completed remote executions and 2 completed CEO provider calls**; Agents still had **2 completed Manager calls and 2 ACK sent**. No paid inference rerun and no duplicate ACK on service restart. **Entire VMs were not rebooted**; machine-level reboot persistence remains an optional independent check.
- Earlier CEO session `level2c-live-20261029` consumed a reservation but was held after an adapter error; next `level2c-live2-20261029` was held after the real GPT-6 API rejected `max_tokens`; neither ambiguous request was retried, refunded, erased, or counted as a successful provider call. They remain available for audit. The provider fix uses `max_completion_tokens`.

## Test results and exclusions

- Control full suite after gateway: **958/958 passed**; after CEO binding correction: **959/959**; after model parameter fix: **960/960 passed**. Source commit `b0aa505` shipped with the change.
- Agents existing full suite after installing locked `psycopg 3.3.2` and OS `libpq5`: **365/365 passed**, rechecked on October 29; Agents production runtime is isolated from the stale mixed-file developer worktree.
- This evidence establishes the **bounded Level 2C preparation exchange**, not the full CEO → Manager → Workers → Manager review → CEO review organization, not actual business/product execution, and not platform production readiness or owner approval.
- Operator files, model tokens, signing seeds and private TLS keys are not committed to Git. There is **no claim of invoice-dollar reconciliation** or proven venture profitability.
- Claude independent source review and acceptance is **pending**; owner remains the only final production authorizer. This is not a request to activate venture spending, payment processing, public customer operations, or launch permissions.
