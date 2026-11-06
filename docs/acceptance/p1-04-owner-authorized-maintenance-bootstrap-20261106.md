# P1-04 owner-authorized maintenance bootstrap — 2026-11-06

Version: 1.0

Scope: one-time adoption of the already implemented C1 broker and C3A/C6 Manager/Worker maintenance controls.

## Owner authorization

On 2026-11-06, the Owner explicitly waived the prior deployment and drain restrictions for this maintenance-controls rollout. This is a narrow, one-time exception for installing and activating the existing maintenance controls. It does not change standing project policy or authorize production CEO activation, customer activity, launch, capital, payment, provider retries, or quota resets.

## Deployment

Source baseline: `a4a578c18643294f358066f47cb78b6c51c301f1` on `main`, with the maintenance implementation already committed and pushed in `b4b38ae` and `fac1879`.

- Venture-Control broker: configured the existing C1 admission path through its systemd EnvironmentFile. The broker was restarted and is active with the expected environment keys. Its pinned gate is OPEN.
- Venture-Agents: installed the pushed C1/C3A/C6 source in the existing Manager package, preserving original file ownership and modes and storing code-only rollback copies under the host backup directory. The installed hashes match source.
- Existing Manager configurations already contained the pinned C3A/C6 admission settings. The three active Managers were restarted and are active. Their shared gate is OPEN.
- Worker A/B/C configs already contained per-identity admission settings. Their source is installed and their gates are OPEN; Worker services remain inactive.

## Live checks

- Broker maintenance object: close/drain succeeded, a new admission request was denied while CLOSED, explicit release succeeded, and admission succeeded again while OPEN.
- Shared Manager maintenance object: close/drain succeeded, a new role admission was denied while CLOSED, explicit release succeeded, and admission succeeded again while OPEN.
- Worker A, B, and C gates: each service identity passed open, close/deny, explicit release, and open checks. These were identity-level checks; the Worker processes were not started.
- Final service state: broker and three Managers active with zero systemd restarts at observation; CEO inactive; Worker A/B/C inactive.
- The two ambiguous provider executions were not queried, retried, edited, or quota-reset during this rollout. The maintenance checks made no direct provider request. The restarted Managers returned to their existing polling behavior; this report is not a provider-call audit.

## Result and limits

The live broker and Manager adoption gap is closed: the deployed services have the tested code/configuration and the shared maintenance gates passed live close/drain/deny/release checks. The controls are OPEN so the existing services continue their prior operation.

This is not full P1-04 production acceptance. It does not establish a complete host-wide writer inventory, end-to-end synthetic venture completion, independent operational review, or Stage 6 approval. Stage 6 was not modified. The production CEO remains inactive, and no Worker service was started.
