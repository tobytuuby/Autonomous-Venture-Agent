# Authenticated shadow advisory handoff — v1.0

Implementation scope authorized by the user's 2026-10-27 instruction. This is a
preparation infrastructure increment, not a new phase or a change to authority.
[Owner approval policy](owner-venture-approval-policy-v1.0.md),
[roadmap v2.3](../project-phase-plan-v2.3.md), and the existing shadow-only
controls remain binding. Venture #1 remains an unapproved pilot.

The new entry point is `agents.ceo.authenticated_handoff`. It does not use the
uncommitted deterministic preparation broker or its self-provisioned identities.
Those protected owner files and their existing timer remain unchanged. A
service-policy attestation from that older lane is never accepted as a CEO
decision without verification against this lane's independently pinned key.

## Trust and automatic delivery

The scheduler has **no private key, signer, key generator, model signing API,
provider call or operational executor**. The operator controls a private ingress
directory and public actor manifest outside model/runtime access. The manifest
uses the existing `{"actors":{"actor-id":{"role":"ceo","public_key":"raw-hex"}}}`
format, with distinct pinned CEO, manager and worker keys. No owner key is needed
or enrolled. Only the trusted operator can change this configuration.

A real trusted signer must independently attest the CEO decision outside the
agent channel. Neither a model response nor possession of advisory text is a
decision. The service requires both:

1. An existing EscalationInbox CEO receipt and Ed25519 signature, bound to the
   fixed venture, item, packet SHA-256, exact advisory-review hash, disposition,
   manager and PREPARATION_ONLY scope, with a current validity window of at most
   24 hours. The receipt's CEO identity must match the pinned CEO actor.
2. A separately signed existing VentureWorkflow `create` command, binding the
   exact handoff hash, workflow ID, genesis revision, version, scope, actor,
   evidence and validity window. This exact signed command is the bounded
   manager assignment the scheduler automatically dispatches. It is prepared
   and signed by the external trusted signer, never by this service or a model.

The private authorization envelope is exactly
`{"decision":{"receipt":{...},"signature":"hex"},"assignment":{"command":{...},"signature":"hex"}}`.
A signed decision already in the source inbox can supply the first component.
No signer is invoked automatically. A receipt alone cannot authorize the
scheduler to invent or sign an assignment. Operator integration must supply the
exact signed command; the ephemeral tests demonstrate this protocol.

The assignment uses the fixed ID `authenticated-2f2366519f2235258b5e3b74`.
Its manager and task list must exactly match the advisory review, its synthetic
effort ceiling is at most three units, and its schema-required `seed_cents`
is exactly one. That field releases no capital and allocates no real funding.
The existing workflow independently verifies signatures, distinct assigned actor
keys, signed handoff binding, genesis, revisions, scope and state transitions.

Source intake reads only the existing scheduled escalation inbox, in a verified,
read-only SQLite snapshot under the scheduler lock. It never touches legacy queue
or provider runtime databases. Packet identity and hash are code-pinned. Advisory
provenance is retained exactly: fixture, operator supplied, or configured provider
not independently verified. Signature verification authenticates attestation and
binding, not the truth of model statements or proof that inference occurred.

## Durable states and failure handling

Missing trust, missing advisory review, missing signed decision or missing signed
assignment persists `PENDING_AUTHENTICATED_DECISION` with a precise reason.
In the deployed empty-trust mode the reason is `NO_OPERATOR_PINNED_CEO_KEY`.
This state reports no manager assignment, no worker execution, no owner approval,
no production CEO attachment, no external action and zero inference. It succeeds
as a scheduler tick so the timer remains healthy.

Malformed, forged, expired, conflicting, stale, widened or corrupt inputs fail
closed as `AUTHENTICATED_HANDOFF_DENIED` (exit 4). Authenticated HOLD/DENIED
decisions persist `AUTHENTICATED_DECISION_HELD` without creating an assignment.
Unverified model rejection cannot issue a signed hold or pivot.

The exact signed authorization is saved privately and fsynced before dispatch.
Workflow transitions and signatures are committed atomically in SQLite; delivery
attempts have a separate verified hash chain. A crash after commit reuses the
same signed command and durable assignment. After receipt expiry an already
committed assignment is historical evidence only; it is never renewed or
re-created. Its private archive and signed workflow lineage are reverified on
restart. New actor commands must still be current and signed. Conflicting
archives/source reviews require operator investigation; no automatic repair,
re-signing, key rotation or rollback occurs.

## Manager/worker preparation loop

The optional private requests directory accepts at most 32 signed apply/worker
envelopes per tick, through the existing control-plane dispatcher. Commands must
target this workflow. It supports bounded delegation, pure synthetic worker
submission, manager improvement/rejection, CEO redirection/revision and advisory
review. Revision retains consumption and the three-unit/one-cent schema bounds.
Manager/worker keys, objectives, venture identity, result hashes and state
lineage remain independently checked. Invalid dependencies remain denied.

The only worker execution available here is the existing fixed in-process
synthetic registry over supplied fixture data. No pilot subprocess, arbitrary
code, shell, browser, network, provider or operational admission is dispatched.
Owner and finance commands are excluded; the advisory loop can end at
OWNER_REVIEW without fabricating owner approval. A real owner discussion and
venture-specific approval remain separate prerequisites for any operational work,
and all live authorities remain denied.

## Operation and isolation

The shipped service and timer run the new entry point. The project-contained
helper starts a **separate transient** hourly timer:

```sh
sudo env -i PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 python3 infrastructure/run-authenticated-handoff.py
systemctl show venture-authenticated-handoff.service -p Result -p ExecMainStatus
systemctl show venture-authenticated-handoff.timer -p ActiveState -p SubState
sudo cat artifacts/authenticated-handoff/state/status.json
```

It creates only root-owned 0700 project artifact directories and an empty 0600
public trust manifest. It does not provision keys, replace existing trust, modify
other timers, copy signed commands to /tmp or install /etc units. It refuses
existing unit replacement. The transient timer disappears on reboot; durable
installation is an operator responsibility and is not claimed.

The service reads private ingress and source state, writes only its dedicated
state, has no network and cannot read provider environment files, venture
runtime, Git or legacy signing identities. Request/authorization files must be
unaliased, operator-owned and inaccessible to group/others. Output never includes
signed commands or exception bodies. The operator must deliver signed data into
these private directories; never stage it in shared/world-readable locations.

Root/operator and trusted repository code are in the trust base. This local
implementation cannot defend against malicious root, replacement of trusted
service code, or rollback of an entire database and audit history. External audit
anchoring and independently controlled deployment source remain future operator
controls. Actor configuration is not proof of real CEO business deliberation.

## Evidence and review

See [execution report](reports/authenticated-handoff-20261027.md) and the
[supplemental scenario runner](../tests/certification/authenticated-handoff-20261027/run_scenarios.py).
Raw signed snapshots and commands stay in ignored private artifacts; the committed
per-scenario decision log contains hashes, transitions and explicit outcomes.
Synthetic signatures use ephemeral test keys only. Production currently has
empty trust and no authenticated CEO decision or assignment. No actual provider,
production manager/worker execution or owner approval is claimed.

This increment does not accept a phase, close Gate 2, or change the ADV universe:
ADV-001 through ADV-049 and /49 remain unchanged. Supplemental scenarios are
reported separately. Independent acceptance remains pending human review.
