# P6.4 Code-First Audit Package

## Purpose

This document is a self-contained audit package for reviewers who cannot access the venture-control bridge to rerun the repository tests. It records the exact source state, implementation controls, focused-test inventory, commands, results, warnings, evidence hashes, and acceptance boundaries. It is descriptive evidence, not a replacement for test execution.

## Source and commit chain

Repository: tobytuuby/Autonomous-Venture-Agent
Branch: main
Remote HEAD at package creation: 2ebfb9aee2c7a1343c79cf38493c797b319bbb4b
Locked configuration fingerprint: 8da59318c29821dc273edc0b027b5cf002111ddbd076a125159c52854ffd0b11

The P6.4 hardening chain is linear:

1. edbf031f2851f0e2d5b715b760f6acbccf7330ed — supplied P6.4 remediation state
2. 5743b8c24d4e36438f1cd5565bb54d845d1b0f23 — Harden P6.4 replay and journal integrity
3. f7b790d5039954e5fdd038971d50d88d03564f45 — Record P6.4 hardening evidence
4. 0f5b0f56b9d021760dc19a1d3dcebd9ade7842dc — Close P6.4 scope and recovery validation gaps
5. 2ebfb9aee2c7a1343c79cf38493c797b319bbb4b — Refresh P6.4 hardening evidence

The implementation commit is 0f5b0f56b9d021760dc19a1d3dcebd9ade7842dc. The evidence commit is 2ebfb9aee2c7a1343c79cf38493c797b319bbb4b.

## Changed-file inventory

The follow-up hardening changed exactly these implementation/test files:

- kernel/p6/operations.py
- schemas/p6/operations-record.schema.json
- tests/p6/test_p6_4_operations.py

The evidence update changed exactly these documentation/evidence files:

- docs/p6-4-remediation-decision.md
- docs/reports/PHASE6-P6.4-CERTIFICATION.md
- docs/reports/PHASE6-P6.4-NON-TECHNICAL-ASSESSMENT.md
- tests/certification/p6-4-config-manifest.json
- tests/certification/p6-4-manifest.json
- tests/certification/p6-4-raw/P6-4.json
- tests/certification/p6-4-raw/p6-regression.json
- tests/certification/p6-4-raw/full-regression.json
- tests/certification/p6-4-raw/remediation.json
- tests/certification/p6-4-raw/git-state.json

Diff from f7b790d to 2ebfb9a: 13 files, 161 insertions, 115 deletions. The audit package itself is an additional documentation-only commit after that evidence state.

## Code-first control map

Source file: kernel/p6/operations.py

- Lines 22-35: evidence_hash is derived from evidence material only: portfolio, venture, target, service, reason, source IDs, source hashes, lineage, and taint.
- Lines 37-42: canonical operation hash excludes canonical_hash, record_hash, status, duplicate, and derived grant_revoked state.
- Lines 44-49: journal record hash excludes only record_hash and duplicate.
- Lines 155-203: submit validates input, enforces idempotency, applies synthetic status, computes canonical_hash and record_hash, and writes atomically.
- Lines 242-262: is_frozen requires portfolio_id and rejects a venture outside the allowed portfolio scope.
- Lines 264-289: replay loads the stored row and verifies JSON shape, current configuration fingerprint, canonical_hash, record_hash, and the database record_hash column before revalidation.
- Lines 300-321: quarantine creates a separate grant-revocation journal record with parent_action_id and independent hashes.
- Lines 323-339: recovery searches journal action IDs and accepts a quarantine only through replay verification; corrupt or invalid candidates are ignored, so recovery fails closed.
- Lines 341-392: validation enforces required envelope fields, policy and fingerprint continuity, portfolio/venture membership, target shape, provenance, synthetic-only effect-free state, live-authority denial, evidence hash, and canonical hash. Direct grant revocation additionally requires an existing verified quarantine parent with matching portfolio, venture, and service scope.

## Schema controls

Schema file: schemas/p6/operations-record.schema.json

The operation enum contains exactly seven operation types:

- freeze
- quarantine
- grant-revocation
- recover
- harvest
- reinvestment-proposal
- wind-down

The schema requires the operation envelope, three hashes, synthetic-only/effect-free constants, and all authority-denial flags. It validates core string, array, source-hash, fingerprint, and hash formats. A conditional rule requires parent_action_id when operation is grant-revocation.

Portfolio/venture membership is an application policy rule, not expressible as a static JSON schema relationship. The code-level scope check is therefore the authoritative control for that relationship.

## Focused test inventory

Source file: tests/p6/test_p6_4_operations.py
Focused denominator: 36

1. test_01_valid_venture_freeze — venture freeze status and effect-free result
2. test_02_service_freeze_is_selective — service-class selectivity
3. test_03_venture_freeze_is_selective — venture isolation
4. test_04_scope_denial — out-of-scope venture rejection
5. test_05_exact_duplicate_converges — exact duplicate convergence
6. test_06_changed_content_collision_denies — changed-content collision rejection
7. test_07_quarantine_revokes_grant_and_preserves_evidence — quarantine and evidence retention
8. test_08_recovery_requires_quarantine — recovery prerequisite
9. test_09_recovery_is_idempotent_and_replayable — recovery replay convergence
10. test_10_harvest_is_synthetic_record — synthetic harvest
11. test_11_reinvestment_is_proposal_only — proposal-only reinvestment
12. test_12_wind_down_is_evidence_only — evidence-only wind-down
13. test_13_unrelated_venture_isolation — unrelated venture isolation
14. test_14_missing_provenance_denies — provenance requirement
15. test_15_fingerprint_mismatch_denies — stale input fingerprint rejection
16. test_16_all_live_authorities_denied — all configured live fields denied
17. test_17_effectful_input_denies — effectful operation rejection
18. test_18_sqlite_reopen_preserves_replay — durable reopen and replay
19. test_19_evidence_hash_is_distinct_and_verified — evidence hash semantics
20. test_20_quarantine_creates_explicit_revocation_record — linked revocation record
21. test_21_idempotency_key_collision_denies — idempotency-key collision
22. test_22_scope_is_mandatory — kernel scope requirement
23. test_23_recovery_cannot_restore_authority — authority restoration denial
24. test_24_tampered_evidence_hash_denies — evidence tamper rejection
25. test_25_grant_revocation_requires_parent — missing parent rejection
26. test_25b_grant_revocation_requires_existing_parent — nonexistent parent rejection
27. test_25c_grant_revocation_parent_scope_must_match — parent scope mismatch rejection
28. test_26_operation_record_matches_schema — quarantine schema validation
29. test_27_replay_rejects_stale_configuration — replay drift rejection
30. test_28_replay_rejects_corrupt_record_hash — persisted hash corruption rejection
31. test_29_replay_rejects_malformed_json — malformed storage rejection
32. test_30_crash_rollback_then_retry_converges — transaction rollback and retry
33. test_31_cross_portfolio_scope_does_not_leak — cross-portfolio isolation
34. test_32_all_operation_types_validate_against_schema — seven operation types and explicit quarantine validation
35. test_33_is_frozen_requires_portfolio_scope — mandatory query scope
36. test_34_recovery_does_not_use_corrupt_quarantine — corrupt recovery candidate fails closed

## Recorded test commands and results

Focused command:
PYTHONPATH=. python3 -m unittest tests.p6.test_p6_4_operations -q
Observed result at implementation commit: Ran 36 tests; OK; exit code 0.

P6 regression command:
PYTHONPATH=. python3 -m unittest tests.p6.test_p6_0_registry tests.p6.test_p6_1_coordination tests.p6.test_p6_2_shared_service tests.p6.test_p6_3_anomaly tests.p6.test_p6_4_operations -q
Observed result at implementation commit: Ran 104 tests; OK; exit code 0.

Full command:
PYTHONPATH=. python3 -m unittest discover -s tests -q
Observed result at implementation commit: Ran 325 tests; OK; exit code 0.
The full run emitted six pre-existing unclosed-SQLite ResourceWarning messages and no test failures.

The raw machine-readable records are:
- tests/certification/p6-4-raw/P6-4.json
- tests/certification/p6-4-raw/p6-regression.json
- tests/certification/p6-4-raw/full-regression.json

## Evidence hashes

- kernel/p6/operations.py: 9604c01e824dcdd4df1362a1d1459187fab46012bd09933ed2ae3cf357991462
- schemas/p6/operations-record.schema.json: 91675df1572c485bd5352055a3068857fc81c33bbdc479476acefef1d702858b
- tests/p6/test_p6_4_operations.py: a2d0695e0ace24716b9280da773e335ed59e494c0037dac1354827debaca75cc
- tests/certification/p6-4-manifest.json: dbb7c1d564ccd623c5233a61feb6d888188fd5d716e19099af7bd1056620b350
- tests/certification/p6-4-config-manifest.json: 19a4b0dee3586de742fcb2ef4a30edfeb8b404de91490d88ed5858e001ee95bd

The final manifest contains SHA-256 hashes for all raw evidence, reports, configuration, and decision files.

## Acceptance state and limitations

At the recorded HEAD, P6.4 is hardening-complete and technically ready for human acceptance. It is not marked accepted. No P6.4-ACCEPTED tag exists. P6.5 has not started.

A reviewer without bridge access can audit provenance, commit lineage, changed-file scope, source hashes, test inventory, command claims, raw result records, and documented warnings from this package. Such a reviewer cannot independently reproduce execution behavior without a runtime; that limitation is explicit rather than hidden.

All work remains synthetic-only, effect-free, fail-closed, and bounded by the locked configuration fingerprint. No live authority or external integration was enabled.
