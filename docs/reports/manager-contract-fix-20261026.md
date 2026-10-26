# Manager response guidance fix — 2026-10-26

Baseline: main at f465f13db66effbf540471b0a82477d50414c536.
Implementation record only; no phase, authority, evidence-class or ADV changes.

The operator's first real OpenAI inference exercise reached evaluation, then
failed manager validation. Read-only, column-limited SQLite inspection confirmed
evaluation completed with a stored response; manager quarantined without a stored
response; review absent; one quarantine event had the fixed detail
"response validation failed". No response content or protected environment was read.
This independently confirms local lifecycle state, not the remote inference itself.
Real OpenAI execution is operator-reported; no live call was made for this fix.

The rejected manager output was not persisted, so its exact failing field cannot
be recovered safely from the available evidence. The old prompt used one evidence
placeholder and symbolic amounts, while validation required three complete,
byte-equal deliverable strings in a fixed order and exact scenario values.

Changes:
- The request describes all three evidence entries explicitly and instructs
  verbatim copying in offer, landing_page_copy, validation_experiment order.
  Object key order may vary; evidence array order remains fixed.
- Each request supplies the selected candidate's calculated revenue and negative
  cost as literal JSON numbers (restock: [10000, -5000]). Templates are copied,
  and response data is never repaired, synthesized or overwritten.
- Existing exact-key, length, count, worker, evidence and arithmetic checks remain.
  Workers remain three bounded local functions; the model receives no tools.
- Durable validation and CLI diagnostics use allowlisted reason codes:
  JSON_INVALID, MANAGER_EVIDENCE_MISMATCH, MANAGER_ARITHMETIC_MISMATCH,
  MANAGER_PACKETS_INVALID, or RESPONSE_INVALID. Exception text and rejected
  model content do not enter these diagnostics. Existing generic runtime
  envelope/tool failures retain their fixed diagnostic.
- Runner fingerprint advances to venture-exercise-v4. Request/response hashes,
  decision lineage, event-chain verification and provenance are preserved.

No automatic format-repair retry was added. Phase 1 policy CEO-009 requires
out-of-schema responses to be rejected or quarantined; current durable terminal
states remain unchanged. Interrupted unrecorded calls retain existing recovery
behavior. Quarantine is terminal: never clear it or retry the old database.

## Operator recovery

Keep artifacts/provider-venture* unchanged as failed-run evidence. Preserve the
user-created infrastructure/venture-ceo-kernel-gate.runtime.json outside Git.
Use the existing authorized configuration and gate setup; do not print secrets.
For a separately authorized operator inference attempt, choose a new unused
basename for the database, its derived decisions.sqlite and decisions.jsonl,
and the report, all inside this repository. Example (not executed by this fix):

```sh
python3 -m agents.ceo.venture_exercise --durable-ceo --require-provider \
  --database artifacts/provider-venture-manager-v4-01.sqlite \
  --report artifacts/provider-venture-manager-v4-01.json
```

If any files for that basename already exist, choose another unused basename.
A further validation failure stays terminal; retain the files and reason code.
Never use the old quarantined state to assess recovery. Success with a fresh DB
must be evaluated separately; prompt guidance cannot guarantee model compliance.

## Validation and decision

Through venture-control asynchronous execution, poll-to-exit and completed local
log reads:
- Focused: python3 -m unittest tests.test_ceo_venture_flow tests.test_venture_exercise
  tests.test_ceo_provider_entrypoint tests.test_ceo_durable tests.test_ceo_provider
  tests.test_ceo_shadow -v — 55 tests, OK, exit 0.
- Regression: python3 -m unittest discover -s tests -v — 667 tests, OK, exit 0
  (existing 663 plus four new tests).
- git diff --check — exit 0.

Raw per-test results and hashes:
[manager-contract-fix-20261026](../../tests/certification/manager-contract-fix-20261026).
The added cases cover independently authored natural prose and reordered keys,
candidate-specific amounts, malformed JSON, references/reordered evidence,
string amounts, forbidden workers/fields, terminal quarantine without retry,
no ledger writes on failure, safe diagnostics, replay and hash-bound provenance.

Review decision: scoped implementation accepted for local validation and operator
review; live recovery and independent acceptance remain pending. Residual risk:
a model may still violate the strict contract or produce poor advisory content.
No new ADV certification is claimed; ADV-001–ADV-049 and /49 are unchanged.
No real CEO was attached or enabled; no token access, live API calls, real capital,
payment, customer contact, launch, deployment or external execution occurred.
