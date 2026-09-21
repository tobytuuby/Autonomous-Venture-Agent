# P7 Execution and Evidence Structure

## v1.0

Status: APPROVED and entered with P7.0.
Reviewer: Kalaap Das, independent reviewer.
Execution class: Synthetic, shadow, or isolated pre-production only.

## 1. Case identity

Every P7 case receives a stable case ID:

P7.<increment>.<control>.<field>.<state>.<sequence>

Examples:
- P7.5.AUTHORITY.network.request.001
- P7.5.AUTHORITY.payment.freeze.001
- P7.5.RECOVERY.revoke.injected-failure.001

Parameterized tests are permitted. The denominator is the number of individually reported case IDs, not the number of test methods.

## 2. Per-case evidence envelope

Each case must emit a JSON record containing:

- case ID and matrix coordinates;
- source commit and source-file hashes;
- configuration fingerprint;
- environment identity;
- command and runner version;
- start/end timestamps and timezone;
- expected disposition;
- observed disposition;
- pass/fail result;
- unauthorized-action result;
- capability/authority fingerprint before and after;
- ledger/provenance hash before and after where applicable;
- raw output path and SHA-256;
- reviewer classification;
- failure, retry, or injected-failure details;
- evidence-preserved timestamp.

## 3. Required artifacts

- p7-execution-manifest.json: denominator, case IDs, source/configuration hashes, environment, commands.
- p7-case-results.jsonl: one immutable line per case ID.
- p7-evidence/: raw outputs, traces, snapshots, and hashes.
- p7-authority-matrix.md: human-readable index of all 81 cases.
- p7-recovery-matrix.md: 12 recovery cases.
- P7-TECHNICAL-CERTIFICATION.md: technical interpretation.
- P7-NON-TECHNICAL-ASSESSMENT.md: governance interpretation.
- P7-REVIEW-DECISION.md: independent review and phase decision.

## 4. Denominator rules

- Authority matrix: exactly 81 required cases.
- Recovery matrix: exactly 12 required cases.
- Additional P7 tests are supplemental and cannot replace denominator cases.
- A missing, duplicate, or non-individualized case record is a denominator failure.
- A parameterized test is valid only when it emits separate evidence for every case ID.

## 5. Blocking-drift preservation

When a blocking drift is detected:

1. freeze the affected scope;
2. create an immutable drift event;
3. capture before/after fingerprints and authoritative-state hashes;
4. record detection time;
5. preserve raw evidence and compute SHA-256;
6. record preservation time;
7. assert preservation time minus detection time is no more than 15 minutes;
8. prohibit recovery or release until independent review.

## 6. Test execution order

P7.0 must first establish the baseline and runtime identity. P7.2–P7.4 must establish recovery, observability, and preservation primitives. P7.5 then runs the 81 authority cases and 12 recovery cases. P7.6 performs independent certification.

No case may use a real credential or create an external side effect.
