# Level2D legacy inference retirement v1.2

This version supersedes the inference actor compatibility allowance in
[v1.1](level2d-multiworker-remediation-v1.1.md), following the owner's scoped
2026-10-31 instruction to retire service-worker from new inference and enable
worker-a/b/c only. All historical specifications and evidence remain intact.
This changes no financial, venture approval, live-action or CEO authority.

New Worker inference policies accept only distinct members of worker-a,
worker-b and worker-c, including the existing single-actor policy format.
The active policy contains all three. service-worker and arbitrary other
actors are denied during policy authorization before a reservation or provider
call, including attempts to execute a previously reserved legacy request.
The legacy trust pin remains available to verify existing signed audit rows.
No historical reservation policy is revalidated or rewritten during accounting.

The existing atomic governor is unchanged: four calls per assignment, the
minimum of current and historical venture policy ceilings across workflows
and epochs, and the independent central daily request/token ceilings.
Retained legacy reservations remain charged. A new workflow, UTC day,
actor, epoch or service restart cannot replenish the venture budget.

Prior independently recorded signed-journal inspection found five retained
reservations for venture-verification against a cumulative ceiling of four.
The existing approved governor therefore permits zero additional Worker calls.
This increment records a denied allocation; it does not invent a grant,
transfer the reasoning allowance, refund PENDING calls, change a cap, introduce
a venture alias or reset any ledger. At least three new calls would require
a separately approved cumulative ceiling of at least eight, implemented through
a versioned governor change reconciling all retained usage. This arithmetic is
not approval. No such cap change is included.

The prepared Control deployment script changes only the installed
agents/ceo/worker_inference.py and worker-inference-policy.json under the existing
Control broker installation. It requires the inspected prior validator hash,
an exactly matching policy except for removal of service-worker, completed
focused tests, an inactive CEO, and explicit operator root execution. It
preserves private backups, checks all historical database table row hashes,
verifies signed journals before/after, preserves trust, restarts only the
broker and restores the two changed files if deployment fails. It never
restores a ledger backup, reserves inference, signs commands or starts a CEO.
Syntax validation is not evidence of executed deployment.

The owner's simultaneous instruction to operate only inside the approved
project root leaves the installed /usr/local/lib target outside that scope.
Applying the prepared script requires clarification that the explicitly
requested safe Control deployment includes that existing installed target.
Until clarified, all task writes stay in the approved project root and
deployment is NOT_RUN.

After that scope is authorized, the concrete deployment command, from the
approved Control checkout after commit/push, is:

```sh
sudo -n python3 -B scripts/level2d_retire_legacy_control.py --apply
```

Run the documented focused test command first to create the script's required
project-local test exit marker. Real A/B/C provider acceptance remains blocked
even after deployment; keep the technical CEO inactive.

On Agents, an authorized operator can stop the old single-worker service with
the following one instruction. This task does not access the Agents project
or claim that the stop was executed:

```sh
sudo systemctl stop venture-level2d-worker.service
```

The distinct worker-a/b/c instance units are separate from that legacy unit.
Their installed policies and service state are not independently verified in
this root-scoped task. No real CEO, capital, payment, launch or provider action
is authorized or used. Supplemental checks leave ADV-001–ADV-049 and /49 unchanged.
