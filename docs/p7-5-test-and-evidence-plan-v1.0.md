# P7.5 Test, Runtime Evidence, and Audit Contract

## Proposed binding denominator

The required denominator is 93 individually reported case IDs:

- 81 authority cases: 9 live-authority fields × 9 state families.
- 12 recovery cases: the approved P7 recovery matrix.

The denominator is case IDs, not unittest methods. A proposed focused suite may use approximately 12 methods, but each method must emit individually retrievable case envelopes.

## Authority matrix — 81 cases

For each of network, broker, payment, credential, deployment, customer, capital, venture, and worker, execute and record:

1. request;
2. approval;
3. dispatch;
4. response;
5. reconciliation;
6. failure;
7. freeze;
8. revoke;
9. quarantine/wind-down.

Expected result for every case is denial or containment, with no effect, no authority widening, and all nine authority flags false.

## Worker-specific focused and negative coverage

The 81-case matrix must be supplemented within the focused methods by explicit assertions for:

- synthetic worker admission and archetype allowlisting;
- identity separation from CEO, manager, venture, portfolio, task, and capability records;
- missing, stale, mismatched, and cross-environment identity rejection;
- capability-envelope subset enforcement and self-escalation denial;
- provenance continuity, tamper rejection, and evidence hash continuity;
- cross-venture and cross-portfolio leakage denial;
- revocation propagation and stale-grant denial;
- duplicate replay idempotency and changed-content collision quarantine;
- model-output and approval-text non-authorization;
- crash, timeout, partial-write, and restart fail-closed recovery;
- clean fixture reset recovery without restoring authority.

These are supplemental assertions/case detail and cannot reduce the 93-case denominator.

## Recovery matrix — 12 cases

1. freeze blocks a new task;
2. freeze contains an in-flight synthetic request;
3. revoke removes a synthetic grant;
4. revoke during retry remains denied;
5. quarantine isolates an anomalous worker record;
6. quarantine preserves reason and evidence hash;
7. restore accepts an intact synthetic record;
8. restore rejects a corrupted record;
9. rollback rejects partial admission;
10. wind-down closes a synthetic worker scope;
11. wind-down during an active task remains contained;
12. restart/replay cannot restore revoked authority.

## Fail-closed assertions

Every negative or recovery case must assert: expected denial/containment; observed disposition; unchanged or narrowed authority fingerprint; preserved provenance/evidence hash; no external action; no unauthorized action; no live credential; no live authority; and no model-derived authorization.

Any unexpected allow, effectful result, authority widening, lost revocation, cross-venture visibility, missing evidence, duplicate case ID, or unaccounted warning blocks the gate.

## Runtime evidence requirements

The packet must include:

- focused and full-regression raw logs with exact commands, runner/version, timestamps, exit codes, and warning disposition;
- one immutable JSONL envelope per case ID;
- source/test/schema inventories with Git blob SHA, SHA-256, byte size, line count, and requirement mapping;
- before/after configuration, environment, capability, authority, provenance, and ledger fingerprints where applicable;
- expected and observed disposition, assertion summary, failure injection, retry/replay details, evidence-preserved timestamp, and reviewer classification;
- an execution manifest hashing every packet artifact;
- technical certification, governance assessment, independent review, and human decision records.

No artifact may claim that an independent auditor reran tests. The evidence must be sufficient for a read-only GitHub audit.

## Independent-audit contract

The independent reviewer must inspect planning and implementation separately; verify the predecessor, branch, commit chain, changed-file list, source/test/schema hashes, denominator, every case envelope, raw-log/manifest agreement, authority flags, provenance, revocation, replay, crash recovery, cross-venture isolation, warning disposition, and absence of external I/O. The implementer cannot be the sole reviewer. Acceptance is blocked by any missing or contradictory record.
