# Preparation control plane VM integration — 2026-10-27

Implementation record against main 1b7d473cb2307893340b994eb451bbd6a447784d.
No policy or phase amendment. Owner approval remains binding; Venture #1 is
unapproved. ADV-001–ADV-049 and /49 are unchanged.

## Configured and executed

All task-created state/configuration is inside the approved project root.
artifacts/preparation-control is root:venture-ceo 0750. Its state directory is
venture-ceo:venture-ceo 0700, requests is root:venture-ceo 0750, request files
are root:venture-ceo 0440, and trust.json is venture-ceo:venture-ceo 0400
with exactly {"actors":{}}. The trust loader requires the executing UID to own
the file; the proposed unit additionally mounts it read-only. No key was
generated, enrolled, loaded or fabricated operationally.

An operator-pinned copy of the Studio escalation packet was submitted as
data to the separate preparation inbox. Packet SHA-256:
2f2366519f2235258b5e3b746a965cf2f9652a2eec0a9f480e05b7a39ee2da4b.
Source is operator-pinned-packet-copy, not an authenticated CEO handoff.
CLI execution as venture-ceo, replay and a fresh-process status read succeeded.
Final preparation status: one inbox item, zero workflows, PREPARATION_ONLY,
zero inference requests and zero external actions. A malformed unsigned
decision was denied (exit 4), then removed from incoming requests into the
protected parent as 002-unsigned-decision.tested. No signed test receipt was
installed in operational state.

## Scheduled inbox and isolation

Read-only SQLite inspection by the trusted operator found studio-online
RECEIVED with that packet hash, null review_source and null decision. The
scheduled status records ESCALATION_AUTHORIZATION_REQUIRED and
PINNED_OPERATOR_BUDGET_GRANT_AND_AUTHENTICATED_CEO_DECISION, zero inference
for its latest tick, and no handoff. Existing provider execution is not
independently verified by this work. The scheduled timer/service was unchanged.

The existing --inbox-database option creates tables and supports mutations;
it is unsuitable as a read-only attachment. No DB link, permission relaxation,
or worker access was added. Using a reviewed packet copy avoids transferring
protected DB access or inventing a decision. Future provider reviews or signed
decisions need a separately reviewed trusted export/import bridge with their
original binding and provenance.

The scoped oneshot adds a private network namespace, IP deny, read-only trust
and incoming paths, and inaccessible scheduled DB, venture runtime, Git,
provider environment files, service home and /run. Only preparation state is
writable in the project. No EnvironmentFile or provider configuration is loaded.
The hourly timer invokes only this offline spool; it grants no model budget.

A separate account was considered. Creating one would modify host account
files outside the approved root and would not meet the requested venture-ceo
execution identity. This installation preparation retains that trusted UID;
it does not start a less trusted worker. Namespace restrictions apply only
when run by the unit. A hostile process under the same UID outside that
namespace is not isolated by Unix ownership and remains a limitation.
Trusted operators can also replace project code/state; external audit
anchoring and signer deployment remain external gates.

Requests are retained and retried. The existing 32-file batch and 5,000-event
delivery limits fail closed; one retained request consumes about 24 delivery
events/day with the hourly timer. Operators must monitor capacity and review
spool archival. No automatic audit deletion or paid retry is configured.

## Installation boundary and exact status

The service and timer pass systemd-analyze verify (exit 0; unrelated installed
xfs units emit deprecated CPUAccounting warnings). They are prepared inside
infrastructure/systemd. Both currently report LoadState=not-found,
ActiveState=inactive, SubState=dead. No systemd restart or timer execution
has occurred. CLI process restart is verified; installed service restart and
active namespace protections are not independently verified.

Persistent installation/enabling requires systemd links outside the project
root. The user was asked to resolve that conflict before those writes. All
authorized root-contained preparation and verification has been performed.
The scoped exception, if granted, permits linking these units, daemon-reload,
starting/restarting the oneshot and enabling the timer; it grants no venture,
provider, signer or paid execution authority.

## Validation and assessment

- python3 -m unittest discover -s tests -v: 791 tests, OK, exit 0.
- python3 -m unittest tests.test_preparation_service tests.test_control_plane
  tests.test_scheduled_ceo_escalation tests.test_scheduled_escalation_intake -v:
  42 tests, OK, exit 0. Includes empty-trust intake/replay/restart/denials and
  existing synthetic signing fixtures confined to temporary test state.
- Operational CLI intake/replay/fresh-process status: exit 0. Unsigned decision:
  denied, exit 4. Unit validation and git diff --check: exit 0.
- Three tracked dirty owner files retain their initial SHA-256 values.
  Existing untracked owner files were not edited or staged.

Raw test and operational logs plus hashes are retained in
tests/certification/preparation-install-20261027. Bridge process IDs:
proc_mvr7997m_40y4dv (PID 1347009, regression) and
proc_mvr79iwj_kb67va (PID 1347990, focused). Both were polled to exited before
completed project logs were read. Bridge process logs are managed by the
required bridge itself, outside the project; task-directed logs are in root.

Assessment: verified local preparation intake and fail-closed command handling;
systemd activation remains pending the filesystem-scope exception. The service
can record intake/advisory data and verify externally signed preparation
commands, but empty actors block every authenticated workflow transition.
No autonomous CEO reasoning, signed handoff, AgentManager inference dispatch,
owner approval, real funding, payment, deployment or launch is enabled.
No real CEO was attached and no real capital action occurred.
