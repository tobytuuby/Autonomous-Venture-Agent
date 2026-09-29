# P9 Increment Audit Reassessment

**Purpose:** Correct the increment audit record with source-verified details and a post-acceptance hardening result.
**Scope:** Synthetic P9 only. P10 remains unauthorized.
**Auditor report reviewed:** User-submitted increment-level audit dated 2026-09-29.
**Remediation source commit:** 36b99e121c6a1fb14747e747d37a07b64141f673.
**Status:** Focused/full tests pass; this follow-up source change awaits independent review before merge to main.

## Findings

### P9.0 — Baseline lock

The predecessor gate was completed procedurally: P8.4 merge ancestry and acceptance were verified before P9 work. The P8.4 feature commit and 59/453 baseline are recorded in the entry/status documents. The original P9 manifest itself records the P8.4 merge hash and P8/P9 test totals, but not the P8.4 feature hash, nor a standalone digest of the all-false authority map. The feature hash is in docs/p9-entry-decision.md and docs/PHASE8_STATUS.md; the manifest's authority map is explicit but was not itself hashed as a distinct fingerprint. baseline-lock.json makes those distinctions explicit and supplies the canonical authority-map SHA-256.

The charter hashes in the P9 tests are synthetic fixtures (a…a and b…b) with fixture venture/portfolio bindings. They are not an external or real pilot charter. No real CEO or live charter was attached. P9's evaluator accepts only a supplied in-memory mapping; it does not authenticate a charter source. This remains a synthetic fixture boundary.

### P9.1 — Evaluator

The implementation manually validates the record contract; it does not invoke a JSON Schema validator at runtime. The schema is separately tested for valid input and all-nine-false denial. The increment audit's “schema validation” wording should be read as schema conformance evidence, not runtime schema-engine invocation. The module imports the internal kernel.p6.registry in addition to Python standard-library modules.

### P9.2 — Malformed enum fail-closed gap and correction

The increment audit's “no gaps” conclusion missed unhashable values. At source commit 78f70e09f81316221400592b39474ef6c7cb8d98, list values in event_type, scope_dimension, requested_control, or current_state could raise raw TypeError during set membership and leave the evaluator unstopped.

Commit 36b99e121c6a1fb14747e747d37a07b64141f673 now validates types before enum membership and quarantines invalid event type, dimension, recovery control, state, or changed-dimensions container with a terminal stop. Existing case 36 now covers these mutations and verifies a later call is rejected. Denominator remains 48 named P9 methods.

### P9.3 — Recovery

Recovery remains a bounded in-memory simulation. Freeze, revoke, quarantine, and wind-down are represented as result states; restore/rollback and terminal reopening are denied. The P9 tests cover these states.

### P9.4 — Evidence and audit

Original P9 evidence remains in the parent certification directory. This supplement adds raw post-remediation P9 and full-regression logs plus a baseline lock. Original P9 acceptance covers its reviewed source commit; the corrective source commit must be independently reviewed before it is merged.

## Post-remediation test results

- P9 focused: 48/48 passed.
- Full regression: 501/501 passed.
- git diff --check: passed.
- No external or live actions were used.

The logs, source commit, baseline lock, and their SHA-256 values are bound in supplement-manifest.json.
