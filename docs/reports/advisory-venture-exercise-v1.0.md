# Advisory venture exercise — implementation evidence v1.0

Date: 2026-10-26. Baseline: main at f8b98bec6548d17dc90aabd065af80a4b97c664d.
Scope: the user's explicit request for a minimal model-driven shadow exercise.
This is an implementation record, not a phase acceptance or live authorization.
The historical offline-only core plan v1.0 and operating-policy draft are unchanged.
The separate exercise adds optional use of the already existing shadow provider;
it grants no network permissions and changes no provider, broker or finance policy.

## Implemented behavior

Run `python3 -m agents.ceo.venture_exercise` from the repository root.
Defaults are `artifacts/venture-exercise.sqlite` and
`artifacts/venture-exercise.json`; both paths must resolve inside the project.
The module defines exact role contracts in SCHEMAS and enforces them with
deterministic validation and the existing orchestration validator.

1. The CEO compares exactly five supplied hypothetical ideas, with rationale and
   risk for each. It selects a supplied idea or shelves every candidate.
2. The manager drafts an offer, landing-page copy and validation experiment,
   then supplies exactly three packets for the existing closed worker registry.
3. Local workers list the supplied business content, calculate scenario surplus
   in integer cents, and prepare unverified research checks. They have no tools.
4. The CEO receives the aggregate and returns a hash-bound advisory review.
5. Only after all responses validate, the existing store persists the synthetic
   venture, full worker flow and nonspendable seed allocation. The JSON report
   retains all three role requests/responses and hashes alongside the ledger.

No model-supplied amount, path, authority, tool or ledger event is accepted.
Duplicate JSON keys, malformed/oversized/nonfinite content, unexpected fields,
duplicate/missing candidate IDs, unknown selections, nonpositive scenario
surplus, altered arithmetic, unbound deliverables, extra/duplicate tasks, unknown
workers, tool proposals and invalid review hashes/dispositions fail closed.
Positive assumed surplus is an exercise arithmetic sanity check, not an approved
business viability threshold. Every live authority envelope has all nine fields
false. The disposition never becomes authorization, even if its text asks for action.

The two initially untracked store files were integrated byte-for-byte, with their
original SHA-256 values preserved:
- kernel/synthetic_venture_store.py:
  95d40491a2c15b17a464ea84e5fe075ce78544d853969d910e3a7daae684057d
- tests/test_synthetic_venture_store.py:
  59371c4332ff2ca2538e431460d63c6ba381c5875227207299d722aa52cdde3b

## Actual inference and evidence classification

All three CEO_MODEL_ENDPOINT/NAME/TOKEN settings and CEO_KERNEL_GATE_FILE were
absent (presence-only inspection; no secret values read into evidence).
This actual end-to-end run used handcrafted fixtures, with zero inference calls.
It is not evidence that an AI evaluated a business or that a live provider worked.

When existing CEO_MODEL_* settings are complete, the same three-stage path calls
OpenAICompatibleShadowModel with an empty tool tuple. The existing pre-model gate
is still required via CEO_KERNEL_GATE_FILE, and its path must be inside the root.
Partial configuration, missing/failed gates, provider errors and invalid responses
stop; they never silently switch to fixtures. No runner/service is attached.
Configured responses are labeled
configured_provider_response_not_independently_verified, including injected test
doubles. Configuration alone is never independently verified AI execution.
The mocked existing transport integration test verifies request construction and
the complete role path; it proves no network reachability or actual inference.

## Reproduced business exercise

All values below are hypothetical, not market research, sales or realized profit.

| Idea | Assumed revenue | Assumed cost | Scenario surplus |
|---|---:|---:|---:|
| Restock checklist kit | $100 | $50 | $50 |
| Freelancer handoff kit | $60 | $40 | $20 |
| Menu costing worksheet | $75 | $60 | $15 |
| Volunteer onboarding kit | $30 | $35 | -$5 |
| Returns tracking worksheet | $40 | $45 | -$5 |

The fixture CEO chose restock for its narrow workflow and higher assumed surplus,
while identifying free reminders and untested willingness to pay as risks.
Deliverables include a $20 printable kit offer, unpublished landing-page copy,
and an offline interview-guide concept with explicit hypothetical success/failure
criteria. No interviews, customer contact, publication or signup occurred.
The arithmetic worker returned 5,000 cents surplus; break-even is three sales.
The CEO review retained the concept for synthetic research and warned that demand,
labor and acquisition assumptions remain unverified.

The persisted event is SYNTHETIC_SEED_ALLOCATION for 5,000 cents, sequence 1,
idempotency key exercise-restock, entry hash
14f167ef7bc79e2ba30dccd975ef85c09b4b61c16a7f6d61f6f4e03e7903b75e.
Available to spend is zero. Reopening SQLite verified the hash chain and returned
the exact stored flow in the JSON report. Repeating the fixture command reproduces
the report and does not add a ledger entry. The canonical report hash (excluding
the file's final newline) is
775ce8565081ad57e6c4a82f86af8036fc49f8b16287962114300a4f21e27c73.
The file-byte SHA-256 is recorded separately in hashes.json.

## Commands and observed results

Commands ran through venture-control asynchronous process execution, followed by
process-list polling to exited and completed log reads. Final raw per-test output,
exercise output and file hashes are preserved in
[tests/certification/venture-exercise-20261026](../../tests/certification/venture-exercise-20261026).

```sh
python3 -m unittest tests.test_venture_exercise tests.test_synthetic_orchestration tests.test_synthetic_venture_store tests.test_ceo_provider tests.test_ceo_shadow -v
# Ran 36 tests in 0.296s; OK; exit_code=0
python3 -m unittest discover -s tests -v
# Ran 640 tests in 1.733s; OK; exit_code=0
python3 -m compileall -q agents broker kernel tests
# No diagnostics; exit_code=0
python3 -m agents.ceo.venture_exercise
# ADVISORY_REVIEW_RECORDED; handcrafted_fixture_no_inference
git diff --check
git diff --cached --check
# No diagnostics
```

There are 17 new tests. They cover actual provider-interface routing with a mocked
transport, alternative advisory selection/content, all-idea shelving, fail-closed
boundaries, instruction text remaining data, authority flags, persistent replay
and CLI report reproducibility. Full regression includes the original five store
tests, preserved unchanged. Initial runs also passed 35/35 focused and 639/639
regression before the alternate-choice test was added.
This is direct local execution evidence, not independent certification.
ADV-001 through ADV-049 and the /49 denominator are unchanged; no new claim of
fresh independent ADV certification or phase-gate acceptance is made.

## Operator assessment and limits

Review decision: implemented and locally validated for advisory synthetic use;
independent acceptance remains with the user. The useful change is that an
existing configured model can supply comparison, selection, planning content and
review, while deterministic code bounds the permitted data and local workers.
The recorded example remains a fixture demonstration because no model is configured.

Workers are in-process functions, not separately spawned AI agents. Supplied
market information is hypothetical. Content quality and factual truth cannot be
established by schema validation. Repeated configured inference is not guaranteed
byte-identical; changed plans conflict with an existing venture registration
rather than silently rewriting it. A new caller-selected local database permits
a separate exercise. The ledger is local synthetic evidence, not tamper-proof
against an operator who can rewrite the database and hashes. The JSON role report
and SQLite ledger are separate files, not an atomic evidence store.
No production durability, pool-wide portfolio enforcement, realized revenue,
80/20 profit distribution, tax handling or unsettled operating-policy rule is added.
No real CEO, capital action, spending, PayPal, customers, launch, deployment,
external research or live external business action was used. No provider request
occurred in this exercise. All nine live authorities remain false.
