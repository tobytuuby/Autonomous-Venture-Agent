# Autonomous Venture Agent — Complete Project Roadmap

## v2.1-DRAFT — Review Remediation

**Status:** Draft for review; not canonical until explicitly approved.  
**Supersedes for review:** `project-phase-plan-v2.0-DRAFT.md`  
**Baseline:** P6.5 accepted at `P6.5-ACCEPTED`; acceptance metadata commit `ba8b8ff777617f33c06caed3c5a8fe328908a31d`.

## 1. Current boundary

P0–P5 are complete for their approved scopes. P6 is complete through P6.5.

P6.5 evidence remains:

- Evidence commit: `89b2399291a48393c6ec3b1092b3b202e3fbfe68`
- Acceptance metadata: `ba8b8ff777617f33c06caed3c5a8fe328908a31d`
- Tag: `P6.5-ACCEPTED`
- Manifest SHA-256: `705d7f25af163e47903408a08fe51b24f8e2b82268ec6b2d83d7743fcbf13563`
- Focused: 12/12; combined P6.0–P6.5: 116/116; full repository: 337/337
- Six pre-existing SQLite `ResourceWarning` messages remain documented; no tests failed.

P7 has not started. All nine live-authority fields and all real external effects remain disabled.

## 2. Complete phase map

| Phase | Name | Execution class | Status |
|---|---|---|---|
| P0 | Policy kernel and certification | Static/synthetic | Complete |
| P1 | CEO shadow hardening and Gate 2 closure | Shadow | Complete |
| P2 | Opportunity and thesis system | Synthetic | Complete |
| P3 | Voyage scout / venture formation | Synthetic | Complete |
| P4 | Venture factory recording-only | Recording-only | Complete |
| P5 | Revenue and ledger systems | Synthetic | Complete |
| P6 | Portfolio and shared services | Synthetic | Complete through P6.5 |
| P7 | Production readiness and controlled-integration preparation | Pre-production rehearsal only | Not started |
| P8 | Limited live pilot | Limited and reversible | Not started |
| P9 | Controlled expansion and production hardening | Approved limits only | Not started |
| P10 | General production and steady-state governance | Approved production operation | Not started |

General go-live occurs only after the P10 exit decision. P8 is a pilot, not general production.

## 3. Quantified cross-phase rules

1. **Test threshold:** An increment cannot pass with a failing required test, regression, negative-control test, or unauthorized-action test. Focused and full-regression denominators must be reported exactly. Pre-existing warnings require disposition and must not conceal failures.
2. **Evidence threshold:** Every claimed result requires a command, source/configuration hash, environment identity, raw result location, and reviewer classification.
3. **Authority threshold:** Every phase must test all nine live-authority fields. A field passes only when both positive-boundary denial and attempted-use negative tests pass.
4. **Recovery threshold:** Freeze, revoke, quarantine, restore, rollback, and wind-down must each have at least one successful rehearsal and one injected-failure case before phase exit, unless the policy explicitly classifies the case as unsafe and provides an approved simulation substitute.
5. **P7 rehearsal scope:** P7.5 must cover all nine live-authority fields across request, approval, dispatch, response, reconciliation, failure, freeze, revoke, quarantine, and wind-down states. No real external side effect is permitted.
6. **P8 pilot minimum:** The pilot charter must specify exactly one venture, one authority class, one operating window, a numeric exposure ceiling, a numeric loss ceiling, named approvers, and automatic stop conditions. “Minimal” is not an acceptance criterion.
7. **P9 expansion dimensions:** Expansion is one dimension at a time from this fixed set: venture count, authority class, exposure ceiling, operating window, provider/dependency, and concurrency. Each dimension requires its own approval and rollback threshold.
8. **P9 independent verification:** Degraded-mode and expansion checks must be reviewed by a person who did not implement the increment. The reviewer must compare capability fingerprints, authority-denial results, audit events, and ledger/provenance hashes before and after the change.
9. **Drift control:** P8/P9 live-state reconciliation must classify drift as zero, tolerated, or blocking. Any unexplained authority, ledger, provenance, credential, or customer-state drift is blocking and triggers freeze. Evidence must be preserved within 15 minutes of detection and retained for the project’s approved audit-retention period.
10. **P10 cadence:** Unless a stricter policy applies, production certification occurs daily for financial/reconciliation controls, weekly for authority/configuration/anomaly controls, monthly for recovery and access review, and after every incident or material change.

## 4. Remaining phase gates

### P7 — Production readiness

P7 proves deployment, recovery, observability, credential custody, authority denial, and complete pre-production rehearsal without real effects. P7 acceptance does not authorize live action.

Required P7 entry artifacts:

- approved roadmap;
- approved remaining-phase implementation plan;
- approved P7 policy specification;
- approved P7 status record;
- approved P7 test/certification matrix;
- explicit P7 entry decision.

### P8 — Limited live pilot

P8 requires a separate written live-action approval and pilot charter with numeric limits. Any failed control blocks expansion and returns the system to the prior safe boundary.

### P9 — Controlled expansion

P9 may change only one predefined expansion dimension at a time. An independent reviewer must verify that authority, configuration, provenance, and ledger boundaries did not widen unexpectedly.

### P10 — General production

P10 establishes service ownership, recurring certification, release governance, suspension authority, and residual-risk acceptance. General production is accepted only after all recurring controls are active and the P10 review is recorded.

## 5. Change control

No phase may be skipped, merged informally, or started solely because implementation appears useful. Changes to phase order, authority, execution class, numeric limits, drift policy, cadence, or exit criteria require a new roadmap revision and impact analysis.

## 6. Current decision

- P6.5: **ACCEPTED**
- P7: **NOT STARTED; ENTRY BLOCKED**
- P8–P10: **PROPOSED; NOT AUTHORIZED**
- Real CEO attachment: **disabled**
- All nine live authorities: **disabled**
