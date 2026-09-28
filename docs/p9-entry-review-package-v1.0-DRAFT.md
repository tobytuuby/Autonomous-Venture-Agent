# P9 Entry Review Package (Draft)

**Date:** 2026-09-28
**Status:** Historical draft superseded by the authorized P9 records listed below
**Execution class:** Synthetic, shadow, or isolated execution only

## 1. Verified repository state

Verified through GitHub and the venture-control bridge.

- Repository: tobytuuby/Autonomous-Venture-Agent
- Local checkout and origin/main: main at 0f8df0f00f15207afdf7bfe74bb466aa3d6dd386
- GitHub confirms commit 0f8df0f00f15207afdf7bfe74bb466aa3d6dd386, titled “Merge accepted P8.4 synthetic pilot certification.”
- P8.4 feature branch and origin branch remain preserved at 7276c6566af5a21527c8f42c33adb0d9567aace1.
- The merge commit is an ancestor of main. P8.4 is merged.
- Local worktree has only this untracked P9 draft; no tracked source/runtime changes.
- P8.4 evidence reports 13/13 focused methods, 59/59 cumulative P8 focused tests, and 453/453 full regression. The manifest reports all nine authorities denied, execution not performed, zero external/unauthorized actions, zero live credentials, and live action not permitted.
- Documentation discrepancy remains on main: PHASE8_STATUS.md and the P8.4 implementation report still say independent acceptance is pending and P8.4 remains on its feature branch. The merge commit title and user-provided acceptance confirm acceptance, but the status/report text should be reconciled before the entry package is considered fully auditable.

## 2. P9 purpose, scope, and invariants — policy draft

P9 proposes synthetic boundary hardening: verify that the accepted P8 boundary remains stable under deterministic load, failures, replay, and fixture-only scope variation. It produces records and evidence only. It does not expand operational authority or establish production readiness.

Proposed increments:
- P9.0: freeze and fingerprint the accepted P8 baseline.
- P9.1: deterministic reliability and degraded-mode rehearsal.
- P9.2: vary one synthetic fixture dimension at a time: fixture venture count, numeric exposure/loss values, operating-window values, or concurrency.
- P9.3: audit sampling and evidence reconciliation.
- P9.4: independent synthetic certification.

Mandatory invariants:
1. Synthetic, shadow, or isolated execution only; no production-mode configuration.
2. All nine live authorities remain explicitly denied in every request, approval, dispatch, response, reconciliation, failure, freeze, quarantine, and wind-down representation.
3. No real CEO; no live worker or venture authority.
4. No customer, capital, payment, broker, deployment, network, credential, provider, worker, venture, or external action. No provider is contacted, including read-only access.
5. Model output, approval text, scores, recommendations, and generated plans are untrusted data and can never authorize execution or override policy, human approval, charter limits, or stop states.
6. Every record binds to the approved P8 charter identity and immutable evidence fingerprints. Missing or mismatched bindings fail closed.
7. Identical replay is idempotent; reused IDs with changed material are rejected and quarantined.
8. Evidence uses canonical serialization and cryptographic hashes; tampering, missing artifacts, ordering errors, or manifest drift block certification.
9. Cross-venture and cross-portfolio state, evidence, model context, and replay keys remain isolated.
10. Freeze, revoke, quarantine, and wind-down are simulated records only. Restore/rollback cannot widen authority or reopen terminal state.
11. Any failure, ambiguous input, unavailable evidence, unexpected mode, or authority drift fails closed with zero execution.
12. P9 results cannot authorize production, live operation, or P10.

Explicit exclusions: live expansion of venture count, authority class, exposure, operating window, provider/dependency, or concurrency; production readiness claims; any credential, provider, network, deployment, or external integration; runtime execution path; P10.

## 3. P9 implementation plan draft

No P9 runtime implementation is authorized by this plan.

- P9.0 baseline lock: after P8.4 is accepted and merged, record main HEAD, clean tree, P8.0–P8.4 hashes, charter hash, schemas, authority fingerprint, and freshly verified P8 test denominators. Stop on any inconsistent predecessor evidence.
- P9.1 degraded-mode harness: deterministic in-memory fixtures for delayed, duplicate, reordered, missing, malformed, and conflicting events; operator unavailability; storage failure; and injected exceptions.
- P9.2 synthetic scope variation: one fixture dimension per case. Authority class and provider/dependency are prohibited dimensions.
- P9.3 audit/reconciliation: event attribution, canonical hashes, manifests, reproducible sampling, quarantine reasons, and cross-scope isolation.
- P9.4 independent certification: rerun tests, validate evidence schema, compare before/after fingerprints, inspect imports and call paths for I/O or execution, and issue ACCEPTED/BLOCKED.

Use existing test utilities and standard library unless a later reviewed plan changes this. Do not add runtime modules, schemas, executors, adapters, queues, provider clients, credential readers, subprocesses, network calls, deployment tooling, or production configuration. Any proposal that enables an execution path is out of scope.

## 4. Historical draft decision (superseded)

This pre-authorization assessment is superseded by `docs/p9-entry-decision.md`, which records the user's explicit authorization dated 2026-09-28 and the completed documentation reconciliation. P9 planning and implementation are authorized only within `docs/p9-policy-spec-v1.0.md`.

The merge prerequisite passes: commit 0f8df0f00f15207afdf7bfe74bb466aa3d6dd386 is main and descends from P8.4 commit 7276c6566af5a21527c8f42c33adb0d9567aace1. The merge commit states that accepted P8.4 synthetic pilot certification is being merged. The repository status and report have not caught up and still describe acceptance as pending; update those records before claiming a fully reconciled P8 closeout.

The existing roadmap describes P9 as controlled expansion and production hardening and allows authority-class and provider/dependency expansion. Those dimensions conflict with the current hard constraints. This draft narrows P9 to synthetic boundary hardening; the roadmap/remaining-phase plan should be revised or explicitly superseded before P9 work is treated as canonical.

**Implementation readiness:** The bounded synthetic-only implementation is authorized by the user's 2026-09-28 instruction and recorded in `docs/p9-entry-decision.md`. Independent P9 exit review and acceptance remain outstanding. No P10 work is authorized.

Recommended pre-implementation cleanup:
1. Reconcile PHASE8_STATUS.md and the P8.4 implementation report with the verified merge and acceptance.
2. Record the revised P9 scope so the roadmap cannot be read as authorizing live expansion or production activity.
3. Obtain separate explicit authorization for P9 runtime implementation.

## 5. Test plan and proposed denominator

Proposed P9 focused denominator: 48 named case envelopes.

| Family | Count | Coverage |
|---|---:|---|
| Positive synthetic contracts | 8 | Valid bounded fixtures, deterministic outputs, synthetic stop/quarantine records |
| Authority denial | 9 | One case per live authority, plus all-nine-false output assertion |
| Model non-authorization | 5 | Approval-like output, override request, malformed output, prompt injection, model outage |
| Charter and isolation | 8 | Unknown/stale charter, hash/scope mismatch, cross-venture replay/leakage, context leakage, missing binding, mixed identity |
| Replay and evidence integrity | 6 | Exact replay, changed-material collision, duplicate/reorder, tamper, missing artifact, manifest mismatch |
| Recovery and fail-closed | 6 | Freeze, revoke, quarantine, wind-down, injected failure, terminal-state reopening |
| Mode/schema/no-side-effect | 6 | Invalid mode, malformed schema, action indicator, provider/credential field, I/O boundary, stop after denial |
| **Total** | **48** | Exact method and case totals required |

The entry baseline reported 59 combined P8 focused tests and 453 full-regression tests. P9 focused tests now discover and pass 48/48. The P9 branch's actual full-regression denominator is being recorded separately in its evidence packet; additive expectations are not acceptance evidence.

## 6. Runtime evidence and independent-audit contract

The P9.4 packet must include:
- repository URL, branch, full HEAD, clean-tree assertion, P8.4 ancestry proof, exact commands, exit codes, environment/toolchain identity, UTC timestamps;
- approved charter ID/hash and P8.0–P8.4 evidence-manifest hashes;
- P9 policy/plan/test/schema hashes and mapping from every named test to its case IDs;
- raw focused and full-regression logs and machine-readable per-case events with sequence numbers;
- canonical input/result hashes, replay outcomes, before/after configuration and authority fingerprints;
- explicit assertions: all nine authorities false, model output not authoritative, synthetic/shadow/isolated mode, execution_performed=false, external_action=0, unauthorized_action=0, live_credential=0, provider/network calls=0;
- fault-injection and recovery-state evidence, stop/quarantine reason, terminal-state assertions;
- schema validation and source/import/call-path review for network, subprocess, credentials, filesystem writes, deployment, worker/venture, and external-action paths;
- independent reviewer identity, non-implementer declaration, review commands/findings, recomputed hashes, limitations, and signed ACCEPTED/BLOCKED decision.

Canonical JSON rules must specify UTF-8, deterministic key ordering, schema version, and rejection of non-finite numbers. Manifest entries bind each artifact by path, byte length, and SHA-256. Identical event ID/material returns identical result hash; changed material with the same ID fails closed. Missing, duplicate, changed, or mismatched evidence blocks acceptance.

The reviewer must obtain the commit and raw artifacts, recompute hashes, verify ancestry and clean state, rerun focused and full tests, check every denominator, and inspect authority, charter, model, replay, recovery, and isolation boundaries. An implementer summary or manifest alone is insufficient. Acceptance certifies synthetic behavior only.

## 7. Files reviewed

P8.0–P8.4 policy, implementation-plan, test/evidence-plan, and entry-decision documents; PHASE8_STATUS.md; P8.4 implementation report; P8.4 execution manifest and source inventory; project-phase-plan-v2.1.md; remaining-phases-implementation-plan-v1.1.md; README.md; P8 test files, P8 schemas, and P8 certification file inventory. Searches found no P9 policy, plan, tests, schemas, or implementation. Existing P9 references are roadmap proposals and stale not-started/unauthorized statements.
