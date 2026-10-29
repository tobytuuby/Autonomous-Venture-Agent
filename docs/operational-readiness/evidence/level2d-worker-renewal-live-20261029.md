# Level 2D Worker mTLS Renewal — Actual Rotation and Final Hierarchy Closeout

Date: October 29, 2026 UTC. **Operator-verified live two-VM evidence; independent auditor verdict pending.** Source commits `3a29aff` and `2589bbb`; real hierarchy operation is documented separately in the preexisting `docs/operational-readiness/evidence/level2d-real-autonomous-hierarchy-20261029.md`.

## Worker renewal controls

- Reused existing OpenBao CA, Control root-only renewal token and twice-separated operating VMs. Restricted `level2d-pki-renewal` token is now allowed `update` on only the added role-specific `pki-venture/sign/or010-worker` path, while unrelated PKI paths remain denied. No CA or root token was copied to Agents.
- Worker `venture-worker` role with separate Ed25519 and mTLS private keys runs on Agents. Dedicated private `worker-renewal` CSR mailbox is accessible only through the mTLS-pinned Worker identity; Manager CSR mailbox remains separate.
- Incoming Worker CSR must have CN `venture-level2d-worker`, a valid signature, no requested X.509 extensions, and the **same public key** as the authenticated Worker client certificate. Broker refuses wrong TLS role with HTTP 403.
- Control signer validates request, signs with OpenBao, pins Worker certificate fingerprint in `VENTURE_BROKER_WORKER_PINS` (retaining at most two pins across rollover), atomically publishes issued cert to the private Worker mailbox and restarts broker.
- Agents root-only `venture-level2d-cert-renew-worker.service`, hourly `venture-level2d-cert-renew-worker.timer`, verifies CA signature, CN, unchanged private-key binding and strictly newer expiry before atomic installation and Worker service restart. Original Manager and CEO/broker renewal services remain enabled.
- Failed first forced CSR test (subject `venture-agents`) was refused HTTP 400 and preserved privately as `pending.bad-cn-20261029.csr`. The client was corrected and tests tightened; no invalid cert was minted.

## Real renewal result

1. Corrected forced request `/usr/local/bin/venture-level2d-cert-renew-worker --force` returned `renewal_worker_pending_signer`; signed CSR subject verified `CN=venture-level2d-worker`.
2. `venture-level2d-cert-renew-control.service` executed on Control, reported **`renewal_control_completed worker`** and restarted the active mTLS broker.
3. Second Worker client invocation returned **`renewal_worker_installed`** and restarted `venture-level2d-worker.service`.
4. New certificate: `CN=venture-level2d-worker`, expires **2026-11-12 15:42:41 UTC**. Both old/new pins temporarily retained for bounded overlap.
5. Post-rotation live Worker authenticated hierarchy status GET returned **HTTP 200**; Worker accessing Manager renewal returned **HTTP 403**; Manager accessing Worker renewal returned **HTTP 403**.
6. Control broker, Control renewal timer, Agents Manager, Agents Worker, and both Agents renewal timers all **active**; finite CEO hierarchy service **Result=success**, inactive after reaching Owner Review.

## Full hierarchy state preserved

The previous real `level2d-acceptance-5` signed chain reached `OWNER_REVIEW`, revision 11: CEO technical genesis, Manager delegation, four real Luna Worker submissions, three Manager improvement requests, Manager acceptance, CEO final review. Independent verification of the stored signed audit chain found **11 transitions with 10 distinct content SHA-256-matched artifacts** and final state `OWNER_REVIEW` with `owner_receipt=None`, `money_released=False`, `operational_authority=False`, `external_actions_allowed=False`. Five actual Manager inference results, four actual Worker inference results, and one actual CEO inference result are durably completed, with central reservations enforced. Service restart verification had no replay of paid inference or signatures. No whole VM reboot has been tested.

## Tests and caveats

- Role-isolated CSR mailbox and mTLS key-binding tests: 17/17 focused pass.
- Control regression after Worker renewal extension: **988/988 passing**.
- No owner approval, live venture admission, finance release, customer operation, or new production authority.
- Cert rotation keeps existing keys; compromise response requires explicit revocation and re-provisioning.
- **Independent Claude source, live-evidence, and final Level 2D acceptance remain pending.** Automated future renewal timers are enabled and their live paths were exercised, but their next expiry-triggered unattended run is necessarily future.
