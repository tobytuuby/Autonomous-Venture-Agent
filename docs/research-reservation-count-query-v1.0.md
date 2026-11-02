# Broker research reservation count query v1.0

Date: 2026-11-02. Baseline: `26923e3cb967872ad6356e2fa7aa8d165b9f34ea`.
Scope: repair CEO visibility of existing internal research reservations. This
implements existing bounded continuation policy; it creates no approval,
inference, launch, payment, production acceptance, or deployment authority.

The CEO previously opened the broker-private `resources.sqlite`, including a
hard-coded installed fallback. Owner-only broker state correctly prevents that
cross-account read. The CEO now uses `HierarchyClient._request` over the existing
broker mTLS listener:

`GET /v1/hierarchy/research-worker-counts/research-<24 lowercase hex>`

Only the existing certificate-pinned `quota-ceo` role can call it. Manager,
Worker, capability and unregistered certificates are denied; HTTP headers and
caller-supplied proposal/round selectors grant nothing. POST is unsupported.
The response contains only `workflow_id`, `snapshot_sha256`, `round`,
`round_count`, and `venture_count`.

The broker opens the existing workflow journal and resources ledger in SQLite
`mode=ro`, without schema initialization, ledger writes, policy changes or
permission changes. A small read-only subclass reuses the existing
`VentureWorkflow.verify` signature and transition verifier. The exact workflow
must exist, its signed ID/venture/full proposal digest must agree, and its round
must be 1–3. Counts reuse `worker_inference.research_charges`, including legacy
round-one charges, retained actor/epoch charges and full proposal attribution.
Historical research reservations must resolve against that verified journal.
No raw reservation records are exposed.

The client rejects malformed counts, wrong identity, stale snapshots and
incorrect rounds. Unavailable databases, malformed retained rows or signature
failures cause denial, never a zero-count fallback. An existing resources ledger
without a reservations table represents zero reservations. The existing CEO hold
path triggers at four reservations in the round (or a smaller configured limit)
or twelve for the proposal. The broker reservation transaction remains the
authoritative race-safe enforcement of the existing 4/12 ceilings; a count
response is observation and grants no reservation.

## Deployment instructions — not executed

1. Use the validated commit, without unrelated workspace edits. Confirm the
   actual installed broker and CEO unit paths with the deployment inventory and
   unit definitions; repository templates do not independently establish live
   bindings.
2. In the existing broker installation, update
   `agents/ceo/hierarchy_gateway.py` and `kernel/broker/isolated_mtls.py`.
   Keep the existing `worker_inference.research_charges`, trusted actor registry,
   mTLS pins, listener, ledger and signed journal. No migration, new environment
   variable, service, endpoint listener or quota configuration is needed.
3. In the existing CEO installation, update
   `agents/ceo/hierarchy_client.py` and
   `agents/ceo/hierarchy_research_daemon.py`. Preserve the configured mTLS
   endpoint, CA, CEO certificate/key, signer and state root.
4. Broker state directories must remain broker-owner-only 0700 and files 0600.
   Do not add CEO/group/other ACL access to broker state, copy the ledger to the
   CEO, or restore the former direct-read fallback.
5. Under separately authorized deployment control, reload the existing broker
   code before the CEO code. Existing processes need their normal controlled
   restart to load Python changes; do not enable a stopped service or initiate
   kickoff, continuation, retries or any workflow for this repair. The template
   units are `venture-control-broker-mtls.service` and
   `venture-owner-research-ceo.service`; verify actual deployed names first.
6. For an already existing approved workflow only, an authorized operator can
   use the configured CEO `HierarchyClient.worker_research_counts(snapshot)`
   for a read-only check. Missing/invalid state must deny. Verify non-CEO
   certificates deny, then inspect existing logs for quota-read errors without
   invoking a role tick or writing a hold. Do not infer live acceptance from the
   isolated evidence below.
7. For rollback, restore the matching prior code through the same deployment
   procedure while retaining private permissions and all state. The old CEO
   direct ledger read will remain unavailable; never loosen ACLs to bypass it.

## Validation and review decision

A clean archive of the baseline plus only the six changed implementation/test
files passed 17 focused and 176 regression tests (both exit 0).
`git diff --check` passed. The working checkout also passed the initial
17-test focused run. Unrelated dirty files were not included in the clean run
or this change. Raw verbose logs, exact commands, runner and SHA256 hashes are
in [the evidence directory](../tests/certification/research-count-query-20261102/).
The runner creates its clean archive and test temporary files inside the project.

Evidence class: independently executed local isolated tests with synthetic
keys/CA, real loopback mTLS, SQLite, signed journals and provider doubles.
Coverage includes role authorization, exact paths, stale responses, corrupt or
missing ledger denial, signed-state tampering, legacy and per-round counts,
unchanged database bytes/0700/0600 permissions, hold error propagation, and
existing round/cumulative reservation enforcement. This is supplemental evidence:
the ADV-001–ADV-049 universe and /49 denominator are unchanged, and no ADV
recertification is claimed.

Review decision: scoped source repair accepted on the local test evidence.
No live deployment, installed-service verification, provider execution, external
market evidence, independent human/Claude/GitHub review or production acceptance
is claimed. Read-only counts can become stale immediately; existing reservation
transactions and signed hold revisions still enforce their own checks.
Privileged rollback/rewrite remains outside journal integrity guarantees.
Operator impact: coordinated code reload is required; errors continue to fail
closed until the broker and CEO have compatible code. No real CEO was attached
or enabled, no workflow was initiated, and no capital or external action was used.
