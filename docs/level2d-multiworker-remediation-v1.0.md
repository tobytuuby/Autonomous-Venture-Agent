# Level2D bounded three-worker remediation v1.0

Review candidate after b7c43e2. No deployment or commit authorized by this document.
This increment retains PREPARATION_ONLY, owner discussion/approval, financial and
live-authority gates. Supplemental tests leave ADV-001–049 and /49 unchanged.

## Observed setup and scope

Inspected repository broker entrypoint, actor registry loader, hierarchy service,
worker provider, OpenBao renewal scripts and systemd units. Also inspected the
existing project-root Control/Agents reconciliation READMEs and the 2026-10-31
blocked acceptance package. Those records describe installed single-worker
routing and leave Agents installed-provider parity unverified. They are historical
observations, not a new inspection of a running service. This task stayed inside
the approved project root; no installed keys, tokens, environment or service
directories were inspected.

Existing runtime uses a Control mTLS broker and the Agents
/usr/local/lib/venture-manager-level2c hierarchy service. Three instances of that
same Python service can run on one Agents host under venture-worker-a,
venture-worker-b and venture-worker-c OS users, with separate 0700 homes/state and
0600 private keys. The new systemd template follows the existing worker service.
No new platform or VM is needed. Separate users/directories are required;
three processes sharing one readable key directory do not provide key isolation.

## Offline staging

All commands below are instructions for later operator review, not executed
deployment. Use the approved checkout and its pinned Python environment. Never
copy a worker private key to Control. Never print a key, token or full environment.

For each worker, run prepare on Agents in a private ignored project artifact
directory. The script creates an independent Ed25519 signing seed, EC TLS key,
CSR and a public enrollment proof signed by that worker. It only prints status.

```sh
python3 -B -m scripts.level2d_worker_provision prepare --actor worker-a --directory artifacts/three-workers/worker-a
python3 -B -m scripts.level2d_worker_provision prepare --actor worker-b --directory artifacts/three-workers/worker-b
python3 -B -m scripts.level2d_worker_provision prepare --actor worker-c --directory artifacts/three-workers/worker-c
```

An exact rerun verifies existing material and does not rotate it. Partial,
aliased, permissive or mismatched material is denied. Investigate partial
provisioning; never remove keys to make a rerun succeed. The enrollment proof
binds actor ID, signing public key and CSR hash. Operator-controlled delivery
and review of these public files is still the enrollment trust ceremony;
self-signing alone does not establish who owns a worker.

Transfer only enrollment.json and client.csr to correspondingly named private
project-root directories on Control. Obtain the public CA chain and the current
public hierarchy trust using approved operator procedures. Keep originals
unchanged. Do not transfer signing.key or client.key.

## CA issuance: explicit operator prerequisite

Live CA issuance was NOT_RUN. No unattended enrollment authority was assumed.
After review, an operator with the existing restricted OpenBao authorization
may issue three separate leaf certificates using or010-worker. The operator
must establish BAO_ADDR and BAO_TOKEN through their existing approved mechanism;
do not put credentials in command arguments, files in Git, terminal output or
chat. Confirm that sudo permits these two environment names and that this token
has only the existing renewal/sign authority. If unavailable, stop and obtain
operator signing; do not generate a replacement CA or self-signed live leaves.

Minimal separate sudo commands, on Control, with public CSR paths in the
approved checkout (shell redirection captures certificates, not private keys):

```sh
sudo -n --preserve-env=BAO_ADDR,BAO_TOKEN bao write -field=certificate pki-venture/sign/or010-worker csr=@artifacts/three-workers/worker-a/client.csr ttl=336h > artifacts/three-workers/worker-a/client.crt
sudo -n --preserve-env=BAO_ADDR,BAO_TOKEN bao write -field=certificate pki-venture/sign/or010-worker csr=@artifacts/three-workers/worker-b/client.csr ttl=336h > artifacts/three-workers/worker-b/client.crt
sudo -n --preserve-env=BAO_ADDR,BAO_TOKEN bao write -field=certificate pki-venture/sign/or010-worker csr=@artifacts/three-workers/worker-c/client.csr ttl=336h > artifacts/three-workers/worker-c/client.crt
```

Set umask 077 before issuance. These are initial issuance commands, not rotation:
skip an already validated certificate rather than overwriting it. A failed
command can leave an empty output; inspect that failure before retrying.
All three CSRs retain CN venture-level2d-worker to reuse the existing PKI role
and renewal mailbox; identity isolation comes from independent TLS keys,
certificate pins, Ed25519 keys, and the actor registry, not distinct CNs.

Enroll only public bundles, validating certificate chain/client purpose,
lifetime, CSR/public-key match, distinct serials, signing keys and TLS keys:

```sh
python3 -B -m scripts.level2d_worker_provision enroll --trust artifacts/current-trust.json --bundles artifacts/three-workers --ca artifacts/ca.crt --output artifacts/three-worker-enrollment
python3 -B -m scripts.level2d_worker_provision configs --endpoint https://venture-control:8443/v1/assignments/pending --policy artifacts/current-worker-policy.json --output artifacts/three-worker-configs
```

Use the actual operator-verified broker port, not the illustrative port above.
Public bundle inputs must be operator-owned 0600 files. Enrollment preserves
legacy trust entries, including service-worker, and refuses conflicting actor
replacement. Candidate output is immutable/idempotent; changed inputs require a
new reviewed output directory. Config generation retains the existing epoch,
model, provider endpoint, request and token ceilings, replacing only the worker
actor list. It never reads installed paths. It renders runtime file names for
later installation; those paths are not a deployment claim.

## Review before any installation

Review candidate trust.json and worker-identities.json, verifying the public
key/CSR bindings through the operator channel. Broker settings must select the
candidate hierarchy trust and VENTURE_BROKER_WORKER_IDENTITIES registry.
Clear VENTURE_BROKER_WORKER_PINS in registry mode: the registry supplies exactly
three pins and renewal replaces one actor's certificate without truncating
siblings. broker-workers.env is a staging fragment; adjust its path to the
eventual protected broker-owned registry, not the staging directory.
Install the reviewed shared worker policy into the existing Control authority
store and the same policy into each worker home. Keep its four-call maximum
and existing central ledger; do not create per-worker ledgers on Control,
reset resources.sqlite or enlarge quotas to get acceptance to pass.

On Agents, provision the three fixed service accounts with no login shell.
For each actor, install only its own signing.key/client.key/client.crt, public
CA, public merged trust, shared policy, rendered hierarchy-config.json and
0700 state directory under /var/lib/venture-worker-X/level2d. Files are 0600,
owned by the corresponding venture-worker-X user. Precreate its renewal
directory under /var/lib/venture-worker-X/renewal for the root renewal unit.
Use infrastructure/systemd/venture-level2d-worker@.service and the corresponding
worker-renew@.service/.timer; instances are worker-a, worker-b and worker-c.
Keep code and units root-owned. No worker gets a CA token or sibling key.

Merge manager-workers.json into a separate technical Manager config, including
workflow_id and decomposition_workers={A: worker-a, B: worker-b, C: worker-c}.
Point the separate technical CEO config/context session_id at
level2d-multiworker-remediation-1, keeping venture_id=venture-verification.
Do not alter existing research-service workflows. Install the reviewed new
bootstrap/gateway and renewal code only after comparing actual service paths
and code hashes; prior staging snapshots do not prove installed parity.

Control renewal reuses or010-worker and actor-specific CSR mailboxes. It rejects
a sibling key, persists a public issuance record for interrupted-install
recovery and records activated registry hashes after a successful broker
restart. Agents fetches certificates through its existing mTLS mailbox and
checks CA/public-key binding before restarting only its own service.
The actor registry has one current certificate per worker. Rotation therefore
has a short old-pin cutover window: the worker downloads the new certificate
using its already established mTLS connection. Retries/restarts and timer
health require operator observation; automatic recovery after expired TLS,
a lost pending CSR, key compromise, or a broken cutover is not certified.
Do not relax pinning to recover; re-enroll through the operator.

## Technical fixture and acceptance

The kickoff now accepts the fresh remediation ID as well as all five legacy
IDs. It creates three scoped tasks under the same venture-verification budget:
A isolation cases, B independent rollback/recovery cases, C consolidation.
The existing Manager callback builds A/B with no dependencies and C depending
on both. CEO signs decomposition approval before workers can act. The legacy
scope worker_id=service-worker remains the compatibility anchor; signed
assignments explicitly name worker-a/b/c. The new gateway requires three tasks
and all three enrolled actors. Budget remains five effort units; Worker
provider calls share the existing venture-wide maximum of four, including
prior calls for that venture. Existing usage can correctly block the fixture.

Required later live acceptance: observe three independently verified TLS actor
bindings; deny sibling impersonation, unapproved decomposition and early C;
complete A/B, release C, consolidate individual digest-bound evidence and
reach OWNER_REVIEW only. Verify durable restart/replay behavior and shared
reservation exhaustion without refund/reset. Preserve raw per-action results,
signed journal and provider receipts. No actual provider journey, issued
live certificate, service restart, or independent reviewer approval is
claimed by local tests. Owner approval and money release remain false.
