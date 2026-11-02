# Historical CEO request recovery — 2026-11-02

Base: c62dfabb9b50cde16fe2c8524797eac3ee1fb23f. Scope: saved internal CEO review recovery only; no deployment or production state mutation.

## Change and review decision

Reconstruct recovery from the exact canonical durable request, not today's prompt. Require its SHA-256 to match the original PENDING request_hash, and the checkpoint snapshot_hash to match the exact workflow returned by the authenticated broker (whose journal verifies signed lineage). Existing artifact content hashes, workflow-derived call identity, CEO actor/model policy binding and durable attempt checks remain enforced. All non-system request fields must exactly match the request derived from that snapshot, including JSON types, goal, scope, round, workflow, evidence and authority semantics. Prompt drift is accepted only for SHA-256 41f163eff0415ca2613f4100e3d5c8fc74e468e39601bd45bbe8a92b14f9ec7b: the exact SYSTEM in c46d160 before af2340e's assessment-bound change. Arbitrary historical prompts remain denied.

Preserve the historical request hash in immutable provider intent. Keep SQLite read-only and the raw response verbatim. Only the existing unique enum-colon decoder normalizes recommendation encoding; every other field still passes the unchanged deterministic validator. No quota reset, new provider request, expanded authority, or durable-request rewrite.

Decision: ready for parent review/deployment, based on isolated software evidence. The signed end-to-end test recovers a historical PENDING review with a unique colon explanation, applies its signed research_disposition through the real workflow gateway, reaches OWNER_REVIEW, reopens and verifies the journal, and confirms unchanged round count, inference database and quota database. All operational/external/financial flags remain false. No real CEO, capital, launch or external action was used.

## Commands and results

`python3 -B tests/acceptance-evidence/ceo-historical-recovery-20261102/validate.py`

The validator extracts a clean HEAD archive inside the approved project root and overlays only the three scoped implementation/test files. It records the exact unittest commands in the raw verbose logs:

- focused.log: 42 tests, OK; focused.exit: 0.
- regression.log: 174 tests, OK; regression.exit: 0.
- git diff --check: exit 0.

The worktree also passed 42 focused and 59 narrower regression tests before clean-archive validation; those preliminary logs remain under artifacts/ceo-historical-recovery-20261102. The initial async run's bridge-managed log was outside approved read roots, so its completion alone is not counted as validation evidence.

SHA256SUMS binds the scoped source, tests, validator, raw reports, exit records and this decision log. These are supplemental compatibility/regression checks. ADV-001–ADV-049 and the /49 denominator are unchanged; no full ADV recertification is claimed.

## Limitations and operator impact

The supplied live request_hash f1412b11b0d1a4e13845a54f8954391b5f2608d542831b4686b7485735652491 and abbreviated snapshot_hash 888ac40... are incident context, not independently inspected production artifacts here. Live workflow research-4e6018e70bf43a549e289b3f was not advanced or deployed by this patch task. The parent must verify its actual checkpoint, durable response and signed workflow after deployment. Any remaining invalid assessment/evidence/task, mismatched immutable intent, stale snapshot, altered request, missing durable response, or model-policy mismatch still fails closed with the corresponding error; this patch does not repair those cases.

Provider output in the tests is an isolated test double. Configured model identity is checked; independent live provider execution/model provenance is not claimed. Existing pinned broker trust and local durable-file integrity remain prerequisites. Unrelated pre-existing worktree changes were preserved and excluded from this commit.
