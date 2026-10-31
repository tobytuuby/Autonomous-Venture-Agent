# Level2D quota diagnosis and bounded operator decision — 2026-10-31

Decision: **BLOCKED; DO_NOT_KICKOFF**. This is an evidence record, not a policy amendment or new approval gate. Source baseline: e1b0ba304d79f89e66f05c9667383797fc3680d9, main, with pre-existing dirty changes preserved.

## Actual Control evidence

At 07:43:37 UTC the installed broker was active (PID 654960), authority enabled at epoch 2 with no revoked actors, and the technical CEO inactive (PID 0). Read-only SQLite inspection and installed VentureWorkflow.verify() verified the full signed journal, including signatures, lineage, transitions and denied operational flags. The configured target level2d-multiworker-remediation-1 under venture-verification has no signed state. No workflow, decomposition approval, HOLD or OWNER_REVIEW result is fabricated.

| Bound | Installed value / usage | Meaning |
| --- | --- | --- |
| Daily central reservations | 30 / 94; 64 remaining | Local Control provider request governor, not provider account balance |
| Daily reserved output tokens | 30,720 / 1,540,096; 1,509,376 remaining | Reserved maxima, not measured billed usage |
| Next daily window | 2026-11-01 00:00 UTC | Natural UTC date partition; no reset performed |
| Shared venture Worker reservations | 5 / 4; effective remaining 0 | All prior workflows/epochs for venture-verification; no renewal window |
| Worker assignment ceiling | 4 | Additional independent bound; cannot replenish shared venture allowance |
| Reasoning request policy | 8 (activation policy evidence) | Separate CEO/Manager allowance; not transferable to Workers |
| Technical scope | 5 effort units, below owner maximum 15 | Effort is not provider requests, output tokens or currency |
| seed_cents | Synthetic scope field | No real spending authorization |

The zero is computed as max(0, 4 - 5), not a zero-valued policy and not daily exhaustion. Four reservations belong to signed level2d-acceptance-5 (OWNER_REVIEW; execution checkpoints COMPLETE); one belongs to level2d-acceptance-3 (WORKER_PENDING; execution checkpoint PENDING). All five charged the daily ledger on October 29. Current shared accounting counts them without a date filter and takes the minimum of current and historical policy ceilings. These rows predate this inspection; their presence does not establish an authorized overrun under today's accounting. PENDING is ambiguous and consumes capacity. COMPLETE is a local checkpoint, not an independently obtained provider receipt. No refunds, deletions or replays were attempted.

The deployed worker governor and signature verifier hashes match the checkout. service_identity.py differs only in its private-directory permission predicate (installed rejects group/other access; the dirty checkout requires exact mode 0700). Its daily limits and accounting code are identical. Local tests exercise the checkout; installed policy and ledger values were inspected separately.

## Existing mechanism and bounded action

Keep the existing technical CEO service inactive and do not invoke scripts/level2d_hierarchy_kickoff.py or reserve inference for this fixture. Leave the broker and waiting Agents services as configured. The target is absent, so a signed workflow HOLD would require creating a workflow first; no such state change is necessary or made. This no-start disposition uses the existing service/kickoff mechanism and does not introduce an approval layer.

There is no legitimate existing Worker quota window for this venture. Waiting until midnight, changing the session/workflow/venture alias, rotating the policy epoch, restarting services or raising only the current policy cannot recover capacity. Historical ceilings remain part of the minimum; the validator also caps the Worker policy at four.

No larger preapproved request or monetary cap was found in the inspected current policies and remediation specifications. To make a later A/B/C exercise possible, the existing versioned budget-resolution process would need to explicitly reconcile retained historical usage and authorize a cumulative cap: five retained reservations plus at least three new Worker calls requires eight; one permitted correction call would require nine. These are arithmetic planning bounds, not authority or an implemented change. A policy-file edit alone is insufficient under the current hard limits and historical-minimum rule. No budget or authority change was made.

## Validation and limits

Executed: read-only installed governor inspection (exit 0); python3 -B -m unittest -v tests.test_worker_inference tests.test_hierarchy_multi_worker tests.test_hierarchy_bootstrap (27 tests, OK); git diff --check. Raw outputs, process provenance, hashes and a separate validation record accompany this file. Tests use isolated synthetic fixtures, including quota concurrency, no refund/reexecution, C dependency denial, and bootstrap behavior; they are supplemental and do not change ADV-001–ADV-049 or /49.

Real A/B/C provider execution, premature-C live denial, Manager synthesis, target CEO OWNER_REVIEW, and target restart/replay acceptance are NOT_RUN because the venture budget is exhausted. The legacy OWNER_REVIEW state is verified but does not satisfy this target. Prior broker activation restart evidence is historical, not a newly executed target recovery test. Agents Manager+3-worker installation/activity is owner-reported for this turn; not independently rechecked through another project root.

This task made zero provider calls and no reservations. Provider-side daily/account availability and historical billed consumption are NOT_INDEPENDENTLY_VERIFIED; no provider probe was forced to establish them. No real/production CEO was enabled, no capital/payment/launch/deployment action occurred, no policy or ledger was changed, and no credentials were exposed.

Inspection development encountered four fail-closed errors before its final successful read: trust ownership check while root; the standard read API's BEGIN IMMEDIATE on a read-only connection; a legacy row missing assignment_id; checkout permission denied after dropping to the broker UID. The final script loads trust as the broker, uses a query-only connection and SELECT after full journal verification, labels legacy assignments explicitly, and restores root only for public source hashes. No error reached a reservation/provider path. Final raw output and exit status are authoritative; process records preserve all attempts.
