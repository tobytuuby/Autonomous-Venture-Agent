# Studio Restock Kit preparation provisioning — v1.0

Operator instructions for the existing authenticated preparation and provider
dispatch entrypoints. This guide grants no authority and changes no policy.
The [owner policy](owner-venture-approval-policy-v1.0.md) and
[authenticated handoff contract](authenticated-shadow-handoff-v1.0.md) remain binding.

## Current blocker

Inspection against a693603 on 2026-10-28 found configured provider credentials
and a locally valid pre-model gate under venture-ceo (UID 993). No network
request was made. This does not verify authentication, endpoint reachability,
provider-side execution restrictions, budget availability or independent
certification. Both installed preparation trust manifests have zero actors.
The studio-online source is RECEIVED with no review or signed CEO decision.
The authenticated ingress has no authorization envelope, operator pin or grant.
No signing identity was generated or enrolled.

The installed deterministic service identities are root-owned preparation
policy attestations. They are not independently attested CEO decisions.
ServiceIdentities.provision must not be used to manufacture this lane's missing
trust, impersonate an operator, or supply owner approval. Changing a signer
label does not change its provenance. The present authenticated verifier expects
an external trusted signer; creating a service key alone cannot satisfy that
requirement. The user's authorization to prepare does not constitute an
externally signed grant or owner receipt.

## Exact secure operator action

The human owner or their authenticated trusted operator must perform these
actions outside the agent/model channel, using independently controlled signing
keys and the approved service credential injection mechanism:

1. Reconcile prior provider requests and any ambiguous charges with the provider.
   Attest an actual remaining inference allowance; do not invent budget or
   reconciliation references. Pin the operator's existing Ed25519 public key
   through trusted configuration. Never pass its private key to an agent,
   request file, provider, repository or signing helper in this runtime.
2. Supply a signed one-request escalation allowance to
   agents.ceo.scheduled_escalation.authorize. Its envelope has grant and signature;
   its grant fields are grant_id, operator, item_id, packet_hash, scope,
   configuration_fingerprint, maximum_requests, budget_reference,
   reconciliation_reference, issued_at and expires_at.
   Bind studio-online, packet hash
   2f2366519f2235258b5e3b746a965cf2f9652a2eec0a9f480e05b7a39ee2da4b,
   SHADOW_PREPARATION_ONLY, the actual configured CEOAgent fingerprint,
   maximum_requests=1 and a current validity window no longer than 24 hours.
   Sign the existing canonical UTF-8 JSON bytes with Ed25519; never sign a
   model-supplied substitute. Run the existing scheduled_exercise entrypoint
   with --escalation-only, --escalation-grant and --operator-public-key.
   The last flag consumes a private file containing raw public-key hex.
   Preserve the existing runner lock, source database and no-retry reservation.
   This step obtains advisory text only.
3. Independently review the resulting exact advisory content and its provenance.
   Pin distinct CEO, manager and worker public keys in the existing actors
   manifest. The trusted external signer must attest both the CEO decision
   receipt and the exact VentureWorkflow create command described in the
   authenticated handoff contract. Bind the exact review, packet, manager,
   tasks, handoff hash, revision, PREPARATION_ONLY scope and validity window.
   The fixed workflow ID is authenticated-2f2366519f2235258b5e3b74.
   Its synthetic effort ceiling is at most three units and seed_cents is
   exactly one; neither field allocates spendable capital.
   Deliver the signed decision/assignment envelope through private ingress.
   Do not relabel the deterministic broker's policy attestation as this receipt.
4. After the existing handoff verifier admits the exact assignment, issue a
   separate provider-dispatch allowance. See
   agents.ceo.provider_dispatch.authorize for the exact envelope. Required
   grant fields are grant_id, scope, assignment_hash, packet_hash, runtime_hash,
   provider_hash, maximum_requests, maximum_output_tokens, budget_reference,
   reconciliation_reference, issued_at and expires_at. Bind
   SHADOW_PREPARATION_ONLY, the complete current assignment, the existing
   runtime_manifest and provider_binding, with at most 47 requests and 16384
   output tokens per response. A smaller allowance is permitted and may stop
   the run before completion. Use a current window of at most 24 hours.
   The separate operator-key JSON is exactly
   {"operator_public_key":"<operator-pinned raw public key hex>"}.
   No sample signature or automatically signed grant is valid evidence.

A signed technical preparation grant is separate from actual human venture
approval. No owner business receipt is required to request this bounded shadow
preparation; operational admission, funding, launch and manager operations still
require Kalaap Das's genuine discussion and exact signed proposal/scope approval.
Owner approval would not lift any live authority restriction.

## Service-account and filesystem handling

Keep new files inside the approved project root, under ignored artifacts.
Prepare separate private handoff state, dispatch state and ingress directories
owned by venture-ceo, mode 0700, with regular unaliased 0600 inputs owned by that
UID. Pin public trust through the trusted operator; never enroll keys from
request data. Source-state remains the existing scheduled-ceo directory.

The existing authenticated-handoff service uses root-owned state. A
venture-ceo process cannot consume it directly. Do not broaden its permissions,
change its timer, copy historical decisions as fresh authority or replace its
empty trust automatically. For a service-account run, the trusted operator
should provision a separate empty handoff state and authenticate the original
signed envelope through the same verifier. Never edit SQLite rows to bypass it.

Both existing provider EnvironmentFiles are root-owned 0600. Have the service
manager inject them into the authorized venture-ceo process, preserving their
order and the legitimate project-local gate. Do not source them in a chat
command, put credentials in argv, print Environment properties, copy tokens
into project files, or make the environment files readable by workers.
Inspect only EnvironmentFiles metadata when auditing systemd.

Once the signed prerequisites exist, the existing CLI consumes these paths:

```sh
python3 -B -m agents.ceo.provider_dispatch \
  --state-dir artifacts/studio-preparation/dispatch \
  --handoff-state artifacts/studio-preparation/handoff \
  --source-state artifacts/scheduled-ceo \
  --trust-file artifacts/studio-preparation/ingress/trust.json \
  --authorization-file artifacts/studio-preparation/ingress/authorization.json \
  --grant-file artifacts/studio-preparation/ingress/provider-grant.json \
  --operator-key-file artifacts/studio-preparation/ingress/operator-key.json
```

This is an entrypoint example, not an instruction to bypass missing signatures.
It requires the injected service environment and correctly provisioned private
paths. Do not enable a timer until a separately reviewed unit confines writes to
those paths and keeps secrets inaccessible to generated worker execution.
Persistent host installation outside the project root remains outside this task.

The authenticated handoff's current systemd namespace denies all networking.
Do not remove that restriction to run inference. Keep provider dispatch separate
from that offline service, with the existing model-only adapter and generated
code containment. Only the trusted harness may run ephemeral loopback HTTP and
browser checks with synthetic data; it grants no remote staging or deployment.

## Completion and evidence requirements

A successful local preflight proves configuration only. Require the complete
provider manager/worker/review chain, actual generated online application,
trusted HTTP and Chromium journeys, and final CEO review. Retain raw request
and response artifacts, redacted transport traces, runtime/dependency hashes,
signed input verification and all failures. Reverify linked bytes on replay.
A model claim that tests ran is insufficient. HOLD or CORRECT is not acceptance.

Keep provider provenance at configured-but-not-independently-verified unless
independent provider execution evidence supports a stronger classification.
Local traces alone do not establish provider-side tool isolation. A Git commit
and SHA-256 manifest make records addressable and tamper-evident; they do not
supply external immutable storage or protect against privileged rollback.
Have an independently controlled audit store anchor the evidence before
claiming immutability. Preserve ADV-001 through ADV-049 and /49; preparation
checks are supplemental.

See the [inspection evidence](../tests/certification/authorization-prerequisites-20261028/)
and [review report](reports/studio-authorization-prerequisites-20261028.md).
