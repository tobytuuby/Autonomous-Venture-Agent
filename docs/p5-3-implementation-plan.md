# P5.3 Implementation Plan — Synthetic Human Review Records

**Status:** Implementation authorized; acceptance pending
**Prerequisite:** Accepted P5.2 at a4dfca0ca9d407b2465c8ebda986ce76e2dd36dc
**Execution class:** Synthetic advisory records only
**Policy scope:** FIN-506, FIN-507, FIN-508, and FIN-509

## Objective

Create durable human-review records for material synthetic financial decisions.
A review records what a human decided and the evidence considered, but it
cannot grant capability, authorize payment, transfer capital, contact a
customer, launch a venture, deploy software, or instantiate a worker.

## Planned and implemented artifacts

- `kernel/p5/review.py`: validated synthetic review ledger.
- `schemas/p5/synthetic-human-review.schema.json`: review record schema.
- `tests/p5/test_p5_3_review.py`: focused boundary and recovery tests.
- `tests/certification/p5-3-manifest.json`: test and evidence manifest.
- `tests/certification/p5-raw/P5-3.json`: raw synthetic evidence.
- `docs/p5-3-certification-report.md`: implementation evidence, not acceptance.

## Required invariants

1. Every record identifies a material question, a human approver, a decision,
   a timestamp, an evidence hash, and the immutable configuration fingerprint.
2. The approver must be explicitly identified as human; model, CEO, manager,
   worker, or ledger identities are rejected.
3. Decisions are advisory records only: `capability_granted: false` and
   `effect: "none"` are mandatory.
4. Duplicate decision delivery converges; changed content under one decision ID
   is denied.
5. Cross-configuration and malformed evidence are denied before persistence.
6. All live-authority fields are fail-closed.
7. SQLite persistence supports durable replay and recovery.
8. Provenance/evidence identity remains visible in the record.

## Acceptance gate

P5.3 acceptance requires focused tests, full regression, schema and manifest
validation, clean diff checks, raw evidence, and separate human acceptance.
P5.4 and all live authority remain blocked.
