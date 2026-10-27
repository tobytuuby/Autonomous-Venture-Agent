# Milestone 1 preparation broker — implementation guide v1.0

2026-10-27. Implementation of the user's bounded signing and handoff directive.
This guide grants no phase acceptance or live authority. The binding
[owner policy](owner-venture-approval-policy-v1.0.md) and historical documents
remain unchanged. ADV-001–ADV-049 and /49 remain unchanged.

## Result and meaning

The scheduled inbox now has a consumer: a deterministic, network-denied service
reads the pinned Studio Restock Kit escalation and records an authenticated,
fixed PREPARATION_ONLY manager assignment in its own durable queue. It does not
attach a production CEO or dispatch the pilot's manager/provider/worker programs.

The three service-owned Ed25519 identities use the existing CEO/manager/worker
protocol roles for compatibility. The CEO-role signature attests only to the
packet identity and fixed preparation scope checked by trusted code. It does
not attest business viability, model reasoning, product acceptance, an owner
conversation, or independently verified provider inference. Model instructions
cannot select the service's scope, tasks, actor identities, budget or signature.

A missing advisory review is explicitly recorded as a hash of null. The service
can still issue its fixed infrastructure preparation assignment. Its local review
is a deterministic policy check, labeled in the summary and signed decision
reference; the existing inbox provenance value operator_supplied means trusted
local service input here. It is never represented as provider output.
An existing advisory HANDOFF remains untrusted content, bound by hash in the
assessment; its instructions are not executed. HOLD/DENIED stop assignment and
put an existing workflow on HOLD. Changed advisory evidence requires trusted
review and does not silently issue a replacement assignment. Any existing source
decision requires separate operator review.

## Storage and trust

All project writes are under the approved project root. Private state and keys
are restricted to ignored artifacts/milestone1-service, directory mode 0700,
seed file mode 0600, root-owned for the deployed service. No owner identity or
owner key is generated, enrolled, loaded or signed. Partial/existing identities
cannot automatically rotate. Public-key manifests pin the three distinct keys;
a mismatch fails closed. The provider service UID cannot read the private seeds.

The service requires privileged read access to the pre-existing venture-ceo-owned
0700 scheduled inbox directory. It runs as root with only CAP_DAC_READ_SEARCH,
a read-only filesystem except its dedicated state, no network, no provider
environment files, no runtime programs or arbitrary command ingress, and
inaccessible venture, Git, credential and legacy queue paths. Repository code
and deployment operators are trusted. This is not isolation against a malicious
root/operator or malicious replacement of service code. Python object privacy is
not a security boundary. Protecting trusted source and externally anchoring
journals remain deployment responsibilities.

The source inbox is opened with SQLite mode=ro inside a coherent verified read
transaction, while holding the existing scheduler lock. The broker never opens
historical queue/workflow databases. Its separate inbox, workflow and signed
requests retain lineage; signed receipt/request bytes are fsynced before
dispatch. A crash after commit replays the recorded assignment; partial,
expired, changed or unverifiable evidence fails closed. Committed assignments
remain historical after receipt expiry and are never automatically renewed.
The seed_cents=1 field is only the existing preparation schema's minimum integer;
it releases no money and is not a funding allocation.

The service tick stops at MANAGER_PENDING. The trusted local apply_preparation
API supports signed manager/worker transitions and the existing pure synthetic
worker registry for repeatable tests. It has no model/request signing endpoint.
The service signer refuses owner actions, CEO business approval and finance
requests. The existing control plane and venture workflow remain signature and
scope verifiers; the operational owner gate remains separate.

## Provider and runtime gates

No new provider invocation is introduced. The existing scheduled_escalation
lane remains the sole separately budgeted review path: it requires an existing
operator-pinned public key, current signed one-call grant, legitimate
configuration/certification, reconciliation reference and durable reservation.
No existing valid grant was available for this implementation; none was minted.
The broker therefore reports PREPARATION_ASSIGNED_PROVIDER_BLOCKED and zero
requests. Its service cannot make provider network calls even if a model asks.

The pilot manager/worker and provider_manager runtimes were inspected and left
unchanged, including dirty owner files. They can run subprocess checks and
generate application artifacts; they are deliberately not dispatched by this
queue. Production attachment, operational admission, provider-backed development,
deployment, launch, outreach and capital actions remain gated. There is no
verified online MVP target; browser acceptance is not claimed or substituted
with a static-prototype journey.

## Local operation

The shipped service/timer definitions describe the restricted configuration.
The project-contained deployment helper starts a transient system timer without
installing files in /etc:

```sh
sudo env -i PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 python3 infrastructure/run-preparation-broker.py
systemctl show venture-preparation-broker.service -p Result -p ExecMainStatus
systemctl show venture-preparation-broker.timer -p ActiveState -p SubState
```

It provisions keys only into an empty private service directory. Existing or
partial identity state requires inspection, never deletion to force a retry.
The transient timer runs hourly and disappears on reboot. Reboot persistence
requires a separately managed unit installation; no persistent installation is
claimed. Re-running the deployment helper while the unit exists fails rather
than replacing that unit. To safely replay the existing service:

```sh
sudo systemctl start venture-preparation-broker.service
```

Review both the service result and private status artifact. BUSY retries on the
next tick with no work. PREPARATION_BROKER_DENIED requires inspection of binding,
permissions, identity pins, source changes or partial state. It never repairs
authority or reopens provider attempts automatically. Initialization failures
can leave a previous status artifact; a failed unit result takes precedence.

## Evidence

[Implementation report](reports/milestone1-20261027.md) separates local synthetic
tests, actual deterministic VM queue delivery, unverified provider execution and
remaining human/phase gates. The supplemental runner preserves per-scenario raw
journal snapshots, public actor manifests, signatures and a decision log. It
stores no private seeds. None of these results constitute independent acceptance.
