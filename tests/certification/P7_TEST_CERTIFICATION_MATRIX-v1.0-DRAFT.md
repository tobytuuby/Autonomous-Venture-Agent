# P7 Test and Certification Matrix

## v1.0-DRAFT

**Status:** Draft for review; execution blocked until P7 entry approval.  
**Policy:** `phase7-policy-spec-v1.0-DRAFT.md`  
**Plan:** `remaining-phases-implementation-plan-v1.1-DRAFT.md`

## 1. Global pass criteria

- Zero failing required tests.
- Zero unauthorized external actions.
- Zero unexplained authority widening.
- Zero unexplained ledger, provenance, credential, or customer-state drift.
- Focused and full-regression denominators declared and preserved.
- Every warning dispositioned.
- Every required result has command, hash, environment, timestamp, raw evidence, and reviewer.

## 2. Increment matrix

| Increment | Required evidence | Minimum pass condition |
|---|---|---|
| P7.0 | P6.5 hashes, clean-tree state, authority baseline | Exact baseline match; all nine fields denied |
| P7.1 | topology, deployment rehearsal, rollback | Two consecutive clean rehearsals; rollback succeeds |
| P7.2 | backup/restore, corruption, service/host loss | Normal and injected-failure recovery pass; corrupted backup rejected |
| P7.3 | alert, incident, escalation, retention drills | All required alerts trigger and are acknowledged; evidence preserved within 15 minutes |
| P7.4 | custody, rotation, revocation, redaction, allowlisting | Normal and failure-injected rotation/revocation pass; no production credential |
| P7.5 | 81-case authority matrix and recovery cases | 9 fields × 9 state families complete; all required tests pass |
| P7.6 | full regression, focused results, independent review | No failures; evidence complete; human certification decision recorded |

## 3. P7.5 authority matrix

The following state families are required for each of the nine authority fields:

1. request;
2. approval;
3. dispatch;
4. response;
5. reconciliation;
6. failure;
7. freeze;
8. revoke;
9. quarantine/wind-down.

**Minimum denominator:** 81 field-state cases. Every case must record pass/fail, expected denial or containment, observed result, evidence reference, and reviewer.

## 4. Recovery matrix

| Control | Normal rehearsal | Injected failure |
|---|---|---|
| Freeze | New action blocked | Freeze during in-flight request |
| Revoke | Grant removed and recorded | Revocation during retry/recovery |
| Quarantine | State isolated and evidence preserved | Quarantine after anomaly |
| Restore | Authoritative state restored | Corrupted/incomplete backup rejected |
| Rollback | Prior safe state restored | Rollback after partial deployment |
| Wind-down | Venture/service closed safely | Wind-down during active task |

## 5. Drift and retention rules

Drift classifications:

- **ZERO:** expected state matches authoritative state;
- **TOLERATED:** pre-declared, bounded, non-authority-affecting difference with reviewer approval;
- **BLOCKING:** unexplained authority, ledger, provenance, credential, customer-state, or policy difference.

Blocking drift freezes the affected scope. Evidence is preserved within 15 minutes and retained for the approved audit-retention period.

## 6. Independent review

The reviewer must compare before/after capability fingerprints, authority-denial results, audit events, and ledger/provenance hashes. The implementer cannot be the sole reviewer.

## 7. Certification decision

The certification report must state:

- exact denominators and results;
- all failures, warnings, retries, and injected failures;
- unauthorized-action result;
- drift classification;
- limitations and unsafe-to-test simulations;
- independent reviewer identity;
- recommendation: ACCEPTED, BLOCKED, PARTIAL, or NOT EXECUTED.

