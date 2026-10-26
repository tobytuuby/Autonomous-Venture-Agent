# Existing Shadow CEO venture-flow integration — v1.0

Date: 2026-10-26. Parent: `8084e5ad17b75a02d3bd9065e85f70a577c25a49`;
initial branch main, clean worktree. User authorization: synthetic implementation
only. No phase, requirement, denominator or authority change is made.

The existing `CEOAgent.shadow_decide` now supports a restricted advisory mode
with no tools and a deterministic response validator. The existing exercise uses
one such agent for evaluation, manager planning and advisory review, sharing its
provider interface and `DurableDecisionStore`. There is no new CEO implementation,
service, action adapter or agent spawning. The existing runner is unchanged.

Use a distinct local database for this milestone:

```sh
python3 -m agents.ceo.venture_exercise --durable-ceo \
  --database artifacts/ceo-venture-flow.sqlite \
  --report artifacts/ceo-venture-flow.json
```

The old exercise API/CLI remains available. Old registry entries remain readable;
adding different provenance to an already registered venture conflicts rather
than silently rewriting history. Durable mode creates sibling `.decisions.sqlite`
and `.decisions.jsonl` files. Derived paths and report/database collisions are
checked inside the approved root. Provider configuration and the pre-model gate
still use the existing interface; partial configuration never selects fixtures.

## Behavior and decision provenance

The same five hypothetical candidates, exact response contracts, JSON parser and
worker validators are reused. Full semantic validation runs before a new durable
CEO response is accepted. Invalid shapes, authority fields, tools, arithmetic,
worker types or review hashes quarantine the decision. Provider exceptions reject
it, without persisting provider exception text. Terminal denied decisions cannot
be retried. Completed and response-recorded decisions replay without model calls;
unrecorded interrupted dispatches retain the existing replayable behavior.
Response persistence and its state transition now share a transaction.

Requests bind each stage to its predecessor decision ID and response hash.
Provenance contains requests/responses, hashes, prompt/model/configuration identity,
durable response hashes and terminal event hashes. The registry includes this
provenance in its existing flow hash and transaction with the nonspendable ledger.
It checks candidate, manager plan, local worker flow, review aggregate, parent
links, configuration and false authority envelopes when writing and reading.
Local functions may be recomputed for validation; no additional actions result.

## Validation and evidence

[Raw evidence](../../tests/certification/ceo-venture-flow-20261026) includes exact
commands/exit codes, per-test logs, fixture report, raw decision records/events,
reopen/replay checks and SHA-256 inventory. Bridge processes were polled to exited
before reading project-local completed logs. Tests ran on the parent plus the
scoped implementation changes; these are direct local execution results.

- Focused unittest command in `commands.json`: **51/51**, exit 0.
- `python3 -m unittest discover -s tests -v`: **652/652**, exit 0.
- `python3 -m compileall -q agents broker kernel tests`: exit 0.
- Durable fixture CLI and replay: exit 0; reports identical, three durable decisions,
  one synthetic allocation, zero available to spend, verified event chain.
- `git diff --check`: exit 0; staged check also required before commit.

Twelve new integration tests cover an injected fake model, persistent replay,
configuration conflicts, failure and authority quarantine, semantic denials,
all-candidate shelving, tool-free enforcement, CLI paths, lineage/tampering,
interruption before response persistence, after response persistence and before
registry insertion. Existing functionality also passes the full regression.
ADV-001–ADV-049 and the `/49` denominator are unchanged. The focused count is not
an ADV certification claim; no new independent phase certification is asserted.

## Assessment and limitations

Classification: synthetic fixtures and injected test doubles; **zero actual
provider inference**. Presence-only inspection found all CEO_MODEL_ENDPOINT,
CEO_MODEL_NAME, CEO_MODEL_TOKEN and CEO_KERNEL_GATE_FILE keys absent. A configured
model was unavailable to this run. No protected environment files, secret values,
credentials or security settings were accessed or changed. No network test or
provider reachability claim is made. Configured responses continue to be labeled
not independently verified; fake-provider tests cannot establish live inference.

Decision: suitable for user review as bounded synthetic implementation, with
independent acceptance pending. Operators can inspect full lineage without
conversation history. Schema checks establish permitted structure, not factual
business quality or market demand. Workers remain in-process local functions.
Decision SQLite, JSONL and registry SQLite are separate files, not a distributed
transaction. A crash before durable response persistence may repeat advisory
inference and duplicate a diagnostic JSONL line; no exactly-once provider guarantee
or concurrent multi-runner guarantee is claimed. Durable decisions prevent repeated
inference after a recorded response, and registry idempotency prevents duplicate
allocation. Local hashes are not tamper-proof against an operator rewriting all
records. Historical rows without provenance remain historical and unenriched.

No real CEO, real capital, spending, payment, customer contact, publishing, launch,
deployment or other external business action was used. All nine live authorities
remain false; an advisory disposition never authorizes execution.
