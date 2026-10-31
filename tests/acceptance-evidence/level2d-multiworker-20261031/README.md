# Level 2D multiworker acceptance — BLOCKED before execution

Observed 2026-10-31 UTC against Control broker PID 4099109.
Source checkout: `44ccadd8919669eca54c04d2a91e6a85f6dfd880`.
Decision: the approved three-distinct-Worker provider journey was **not executed**.
This package records completed prerequisite inspection and local tests only.

The active broker's configured hierarchy trust contains exactly three actors:
`service-ceo` (CEO), `service-manager` (Manager), and **one** Worker,
`service-worker`. Both Worker reservation and execution closures hard-code
`actor="service-worker"`. The two configured Worker TLS pins route to the
same Worker role; their presence does not establish distinct Worker identities.
The live single-actor policy is enabled at epoch 2, model `gpt-6-luna`,
1024 maximum output tokens and four shared Worker requests.
The authorization code requires both the supplied Worker identity and the
operator policy's actor_id to equal the broker-bound actor.

The deployed technical bootstrap additionally accepts only
`level2d-acceptance-1` through `level2d-acceptance-5`.
The inspected CEO config still targets `level2d-acceptance-5`.
The new fixture plan uses `level2d-multiworker-20261031-01`; it was never
submitted, created, signed, or substituted into an existing workflow.
See the numbered deployed source excerpts and hashes in
[control-observation.json](control-observation.json). The runner supports
assignment selection, dependency readiness, and actor-keyed signers in code;
that does not provision distinct authorized live Workers.

To make this journey possible, the existing deployment needs three separately
pinned Worker signing identities, corresponding actor-bound TLS authorization
and policies, and a narrow admission path for the new technical fixture.
A safe change must preserve the shared atomic four-call ceiling and avoid
routing sibling identities through one actor. This is a deployment prerequisite,
not something this evidence package silently enables. Agents services and
credentials were not inspected after the blocking Control prerequisite failed;
their individual configuration remains unverified.

| Requested evidence | Result for this attempt |
|---|---|
| Signed CEO create, Manager proposal, CEO approval | NOT_RUN; no commands or signatures generated |
| Actual provider inference by three distinct Workers | NOT_RUN; no provider requests initiated by this attempt |
| C early denial then dependency release | NOT_RUN live; local tests only |
| Shared atomic budget and four-call cap | Policy/source inspected; local tests only |
| Identity denial | NOT_RUN on deployed service; local tests only |
| Consolidation, CEO OWNER_REVIEW, signed audit chain | NOT_RUN; no live transitions or audit chain created |
| Provider receipts, usage, token totals | Unavailable; no inference performed by this attempt |
| Service restart and inference replay protection | NOT_RUN live; no completed test workflow to recover |

No service restart was warranted while the prerequisite failed. The active
broker also serves existing research; restarting it would add disruption without
validating this journey. No services, broker, credentials or persistent runtime
database were created or modified. No workflow was overwritten. No production
CEO, venture launch, external business operation, capital or payment action was
used. Existing dirty tracked files were fingerprinted and preserved.
Temporary local test artifacts stay under the approved project root's ignored
`artifacts/level2d-multiworker-20261031/tmp`.

Validation: **48 local tests passed**, exit 0, in 7.332 seconds. The raw per-test
output is [local-tests.log](local-tests.log). Tests cover signed decomposition,
blocked C, evidence consolidation, concurrent shared reservations, four-call
exhaustion, cached retries, identity checks and local TLS behavior. They use
fixtures/fake inference and local test servers; they do **not** prove deployed
provider execution, business readiness or independent auditor acceptance.
The ADV universe and /49 denominator are unchanged; these are supplemental tests.

[execution.json](execution.json) records commands, process IDs, bridge log paths,
inspection limitations and preliminary tooling failures. [fixture.json](fixture.json)
is an uncreated plan, not an authorization or execution receipt.
[inspect_control.py](inspect_control.py) reproduces the allowlisted read-only
inspection through existing Control sudo access. It never emits the complete
environment, signing keys, certificates, credentials or prompts.

Run the offline verifier from the project root:

```sh
python3 tests/acceptance-evidence/level2d-multiworker-20261031/verify.py
```

It checks artifact byte hashes, canonical JSON hashes, observation consistency,
the explicit NOT_RUN evidence classes, local test results and preserved dirty
tracked files. Its successful result verifies this **blocker evidence**, never
live acceptance. Hashes are integrity checks, not signed provenance or independent
attestation of observation accuracy. Source hashes describe deployed files on disk,
not a byte-for-byte measurement of Python code in the running process. The
observation is a point-in-time operator inspection, not a provider audit.
