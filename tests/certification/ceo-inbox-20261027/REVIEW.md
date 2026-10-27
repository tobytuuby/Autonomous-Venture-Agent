# CEO inbox implementation evidence and review decision

Baseline: main d0c06a5bf2ec260a752f741a8bc923143ea63e18, verified before work. All repository operations used venture-control in the approved project root. This is local supplemental workflow validation, not ADV recertification or phase acceptance. ADV-001–ADV-049 and /49 are unchanged.

## Commands, raw evidence and failures

| Command / revision | Raw output | Exact result |
| --- | --- | --- |
| python3 -m unittest tests.test_ceo_escalation_inbox -v | focused.log | 12 tests, OK |
| python3 -m unittest tests.test_ceo_escalation_inbox tests.test_ceo_durable tests.test_advisory_queue -v; after adding export audit | focused-final.log | 24 tests, 1 failure |
| python3 -m unittest discover -s tests -v; same revision | full.log | 724 tests, 1 failure |
| focused command above; corrected expectation and added bounds cases | focused-verified.log | 26 tests, OK, exit 0 |
| full command above; same revision | full-verified.log | 726 tests, OK, exit 0 |
| focused command above; final venture-bound receipt | focused-bound.log | 26 tests, OK, exit 0 |
| full command above; final venture-bound receipt | full-bound.log | 726 tests, OK, exit 0 |

The failed assertion expected a decision replay to equal the pre-export snapshot. The new audit event correctly persisted handoff_exported=true. The test expectation was corrected and now also checks that repeated handoff export creates no duplicate event. Both failed raw logs are retained. No failure is hidden or described as a pass.

Final combined focused run: process proc_mvqz4ma3_rlt5ae, PID 1213709, returned bridge log path /home/epsilon/.chatgpt2localbridge/process-logs/proc_mvqz4ma3_rlt5ae.log. Root-local raw test outputs were redirected to artifacts/ceo-inbox-focused-bound.log and artifacts/ceo-inbox-full-bound.log, then copied here after bridge process_list confirmed exit. Exit files independently reported 0 and 0. Logs were read through the bridge inside the project root; no out-of-root log access was needed.

Raw verbose logs preserve a result for each named test. The 14 new scenarios cover intake hash/provenance/restart, concurrent atomic idempotency, rollback, strict schema and lineage denial, missing/wrong signing authority, signed fixture handoff only, manager mismatch, receipt expiry and key rotation, HOLD/DENIED final states, CLI and path limits, input/ack conflicts, audit/state tampering, review replay/immutability/event capacity, and validity/file-mode bounds. Each is local synthetic evidence. Existing durable-state and advisory-queue cases are regression coverage; they do not show automatic dynamic intake.

checks.log records git diff --check (exit 0), SHA-256 verification of all three unrelated dirty tracked files (all OK), and byte comparison of the unrelated tracked diff (exit 0). unrelated-tracked.sha256 preserves their hashes. These preservation hashes were captured before regression, after initial inbox-only edits; no writes to those tracked files occurred during this task. Existing untracked runtime evidence was neither staged nor edited by this implementation. It was not exhaustively independently rehashed.

## Authority, provenance and operator assessment

The actual Studio Restock Kit escalation is used as test packet data. Its SHA-256 is included in SHA256SUMS. Reviews and Ed25519 keys/signatures in tests are explicitly synthetic fixtures. No real CEO decision, owner discussion, provider inference or model approval is claimed. There was no provider call or fallback. No actual pilot inbox decision was recorded.

The new API defaults to no CEO key, so handoff fails closed until a separately authorized trusted control-plane signer adapter exists. Review alone is never permission. A signed receipt binds venture, intake ID/hash, exact review hash, manager, scope and validity. Handoff exports preparation records only and records first export; it executes nothing. No signing key, key enrollment endpoint or worker executor is supplied.

Operators gain durable ingestion/read/ack and a review/decision record API. The fixed scheduled CEO replay and advisory queue remain unwired to it. Safe signer identity/configuration, service wiring, deployment isolation, key revocation, external anchoring and any operational execution path require separate work. Local hashing cannot detect coordinated whole-database replacement/rollback; signatures attest signer claims rather than independently proving reasoning or discussion. See docs/ceo-escalation-inbox-v1.0.md for the executable strict contract and usage.

Review decision: implementation and observed tests support local preparation workflow review only. There is no operational approval, product acceptance or production readiness claim. All live authority gates, budgets and owner approval requirements remain unchanged; venture-001 remains unapproved. No real CEO attachment, capital action, secret access, service deployment or worker autoexecution was used.

## Artifact integrity

SHA256SUMS binds source, tests, guide, packet, this review, raw logs, check results and exit summary. It is a local integrity inventory, not an independently anchored attestation. The final Git commit identifies the delivered files; the pre-existing dirty kernel changes were present during full tests and were excluded from the commit.
