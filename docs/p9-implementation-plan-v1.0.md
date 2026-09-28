# P9 Synthetic Boundary Hardening — Implementation Plan

**Version:** 1.0
**Authorization:** Kalaap Das authorized P9 planning and implementation on 2026-09-28
**Branch:** phase9/p9-synthetic-boundary-hardening
**Base:** main at P8.4 merge 0f8df0f00f15207afdf7bfe74bb466aa3d6dd386

## P9.0 — Baseline lock

Record main ancestry, P8.4 merge/feature commit, approved charter identity, source/schema hashes, all-nine-false fingerprint, and exact P8 focused/full regression totals. Refuse to create the P9 baseline if a predecessor hash or acceptance record disagrees with the repository.

## P9.1 — In-memory boundary evaluator

Add one standard-library-only module under kernel/p9. Accept an in-memory charter mapping and one synthetic event at a time. Validate mode, schema, charter/venture/portfolio binding, allowed fixture dimension, all authority/action flags, sequence, and deterministic content hash. Return an effect-free simulated, quarantined, or denied result. Do not read configuration or evidence from disk.

## P9.2 — Replay, isolation, and fault containment

Use in-memory event/result maps only. Exact replay returns the same result. Changed material under an existing ID stops the boundary. Maintain sequence independently by venture/portfolio. Injected failure creates terminal fail-closed state. Tests prove that IDs and state do not cross scopes.

## P9.3 — Synthetic recovery simulation

Represent freeze, revoke, quarantine, and wind-down as bounded result-state values. Deny restore, rollback, and reopening revoked/wound-down state. These are records only; they do not perform recovery or change external state.

## P9.4 — Certification and audit

Run focused P9 cases and the complete repository suite. Preserve raw outputs, case registry/results, source/schema/test inventories, commit identity, environment/command metadata, all-nine-false authority fingerprint, zero-action counters, and artifact hashes. An independent reviewer must recompute hashes, check denominators and scope bindings, inspect imports/call paths, and issue ACCEPTED or BLOCKED.

## Files

- kernel/p9/synthetic_boundary.py
- schemas/p9/p9-synthetic-record.schema.json
- tests/p9/test_p9_synthetic_boundary.py
- tests/certification/p9/ manifest, focused/full logs, case results, source inventory, and audit report
- docs/p9-policy-spec-v1.0.md
- docs/p9-implementation-plan-v1.0.md
- docs/p9-test-and-evidence-plan-v1.0.md
- docs/p9-entry-decision.md
- docs/PHASE9_STATUS.md

## Stop conditions

Stop and fail closed on any authority bit not false, execution or external-action indicator, model authorization signal, charter/hash mismatch, evidence tampering, replay collision, cross-scope leakage, sequence violation, malformed/non-finite input, injected failure, or terminal-state reopening attempt. Preserve local test evidence and do not retry past a stop.

This plan authorizes only the code and tests described above. It does not authorize P10 or any live, production, credential, provider, or external action.
