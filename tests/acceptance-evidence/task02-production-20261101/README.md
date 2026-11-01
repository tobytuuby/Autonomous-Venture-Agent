# Task 02 production acceptance evidence

**Observed:** 2026-11-01 UTC
**Control repository:** `df363cd5a90d06fc99264a91f035f44a15ac7a38` (`main`, pushed)
**CTKFamily repository:** `92fe0ce` (`release/resume-p1-p2-20261019`, pushed)

## Production execution

The existing Owner-approved proposals continued without a second Owner review. Real signed CEO → Manager → Worker work was recorded in the existing research workflows and central reservation ledger.

| Venture | Workflow | Worker reservations by round | Current state |
|---|---|---:|---|
| Volunteer Shift Reminder Planner | `research-c477fcaa9ad6bdbeda36aef7` | R1 4, R2 4, R3 0 | CEO terminal `REJECT_OR_DEFER` |
| Freelance Client Intake Kit | `research-206691adb1574f2c166f57e3` | R1 4, R2 4, R3 4 | CEO terminal `REJECT_OR_DEFER` |
| Tutor Lesson Recap Builder | `research-59bc909391fc057b288d856f` | R1 4, R2 4, R3 0 | CEO terminal `REJECT_OR_DEFER` |

Round 2 received a fresh allowance of four Worker calls for each proposal. R3 usage stayed within the same per-round limit and cumulative 12-call cap. The signed research journal kept correction cycles separate from research rounds. R3 produced terminal CEO decisions; no launch, customer operation, or capital release was authorized.

## Limits and financial authority

- Existing `resources.sqlite` records show 48 central reservations and 49,152 reserved tokens on 2026-11-01 at verification. Existing central quota policy was unchanged.
- Per-proposal Worker reservations are 4 per round and at most 12 cumulatively across R1–R3. The ledger records proposal digests and round numbers, so a workflow alias cannot renew the allowance.
- Costs and available venture financial authority are not tracked by the current authority store. The Owner API returns null for both; CTKFamily displays **Unavailable**, not a fabricated zero.
- Existing worker policy remains at four requests and 1,024 output tokens per Worker identity per round. No limits or authorization records were increased.

## Owner API and CTKFamily

The existing publication unit now passes the actual broker ledger path to `publish_owner_research_status.py`. Without that path the publisher selected a nonexistent CEO-local database and failed. The change preserves the broker ledger's existing restrictive permissions and writes only the already-defined sanitized Owner status file.

The publication service completed successfully at 2026-11-01 16:50 UTC. A live mTLS `GET /v1/owner/ideas` returned HTTP 200 with all three records at Round 3 / 3, zero remaining rounds, accurate per-round and cumulative Worker usage, signed terminal recommendations, exhaustion, and Owner-action state. The website's existing Venture Management page reads this response and displays the continuation fields; its contract test passed. The legacy “Awaiting renewed scope/authorization” fallback is suppressed when the continuation object is present.

## Runtime and verification

- Control broker, Owner API, and Owner research CEO units: active/running.
- Agents VM Manager and Workers A, B, and C: active/running.
- Deployed CEO review file SHA-256: `989a89c347ee6c0ec9ef987a6a9d6b055b752c4bf3fa3d9ded4ff1b5b26de749` (matches source at `df363cd`).
- Focused regression set: **77 tests passed** (`test_research_continuation`, hierarchy service/roles/gateway/runner, Worker inference, Owner research progress/admission, multi-worker hierarchy, and CEO research review).
- CTKFamily: `php -l pages/venture_ideas.php`, `php tests/venture_ideas_contract_test.php`, and `git diff --check` passed.
- The CEO-review regression specifically verifies that signed evidence from an earlier, differently-scoped research round is reused for the next decision. This fixed the Tutor workflow's R3 Manager escalation, which had no artifact in the latest scope but did have prior evidence in its signed journal.

Production review remains internal and preparation-only. No Owner approval, launch action, external contact, or capital release was created by this work.
