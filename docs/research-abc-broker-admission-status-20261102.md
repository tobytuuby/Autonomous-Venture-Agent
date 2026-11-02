# Research A/B/C broker admission — 2026-11-02

Implementation and isolated signed validation; deployment blocked.
Source baseline: main at 6a6a01810607fb8b96196fecd8568658dfedeb8d.
Follow-up to research-abc-integration-status-20261102.md; no policy change.

## Scoped change

Adopt the existing one-line hierarchy_gateway.py research bootstrap restriction:
new research requires worker-a instead of service-worker. Technical acceptance
fixtures retain their existing service-worker scope. Owner proposal digest,
signed CEO handoff, command signature, budget, and PREPARATION_ONLY checks remain
in force. No broader admission or legacy research bootstrap is added.

tests/test_owner_research_admission.py already had the corresponding worker-a
scope update in the dirty tree. Integrate it with a distinct generated worker-a
public key: its preexisting alias reused service-worker's key and violated pinned
key isolation. tests/test_mvp_handoff.py now submits its disposition-denial probe
as worker-a so it reaches the intended immutable-disposition check.

New tests/test_research_broker_admission.py exercises real Ed25519 signatures and
durable journal state: valid bootstrap/replay/reopen; legacy, sibling and unknown
scope worker rejection; unauthorized signers; signed-content tampering; Owner
approval revocation; objective/handoff/digest mismatch; live/money/budget override
denial; and unchanged reads of a previously signed legacy record. Historical
records are simulated in isolated fixtures through the journal API.

No actual installed signed workflow was migrated, re-signed, or written,
including Client Document Checklist research-5900c3db9bb5bd74601e3f9d.
Its installed bytes/state were not independently verified within this scope.

## Validation and evidence

Python 3.14.4, generated fixture keys, fake inference, temporary state within the
approved project root. Evidence:
tests/acceptance-evidence/research-abc-admission-20261102/.

- Focused command: python3 -B -m unittest tests.test_research_broker_admission
  tests.test_owner_research_admission tests.test_research_abc_routing -v
  — 13 tests, OK, exit 0.
- Expanded command: exact 20-module invocation in test-command.txt
  — 166 tests, OK, exit 0 in the dirty tree.
- Same expanded command in an isolated HEAD archive plus exactly the gateway,
  admission fixture, new admission tests and dependent MVP test updates
  — 166 tests, OK, exit 0.
- Expanded tests cover signed research round two, A/B/C dependencies,
  continuation limits, inference boundaries and denied MVP/finance operations.
- Initial focused run: 13 tests, one error because the new test expected
  ValueError instead of cryptography.InvalidSignature. Corrected test expectation.
- Initial expanded clean and dirty runs: 166 tests each, one failure each from the
  dependent MVP probe's legacy actor. Corrected to the scoped actor as above.
  Initial and final per-test logs and exit codes are retained. The two initial
  expanded logs are gzip-compressed byte-for-byte to retain unittest trailing
  spaces without introducing whitespace errors into the Git patch.
- SHA256 comparison of 644 accessible preexisting dirty paths: 643 unchanged;
  only the necessary admission fixture changed. The gateway bytes match the
  preexisting one-line change exactly. Unlisted inaccessible runtime directories
  were not inspected. Unrelated dirty work remains uncommitted.
- ADV-001–ADV-049 and /49 are unchanged. These tests are supplemental; full ADV
  recertification was not run.

validate.py records the archive/copy/test procedure. SHA256SUMS binds the sanitized
raw per-test logs, commands, exit codes, inspection and preservation records.
The original archive and baseline hashes remain in ignored project artifacts.
git diff --check and staged diff review are required before commit.

## Installed inspection and precise blocker

Read-only venture-control systemctl show metadata independently observed:
venture-control-broker-mtls.service and venture-owner-research-ceo.service were
loaded/active/running. Their WorkingDirectory values are respectively
/usr/local/lib/venture-control-broker-level2c and
/usr/local/lib/venture-ceo-level2c. The kickoff unit is loaded and was inactive
between scheduled runs. CEO/kickoff ExecStart references hierarchy-config.json
under the installed CEO directory. These observations prove service metadata,
not installed code revision, configuration correctness, trust alignment,
provider execution or research progress.

venture-agents workspace discovery returns
/home/epsilon/venture-agents-workspace. A shell inspection through that bridge
using this task's sole approved root /home/epsilon/venture-control-workspace
failed with ENOENT / INVALID_ARGUMENT. No operation was run in the other root.
Agents installed services/configuration/trust remain unverified.

Repository unit templates were inspected. They reference installed CEO config,
Manager config under /var/lib/venture-manager/level2d, and worker config under
/var/lib/venture-worker/level2d or /var/lib/venture-worker-{a,b,c}/level2d.
They also retain a legacy single-worker research unit. Templates do not establish
which bindings are installed on Agents. No config, trust, signing key, provider
secret, installed code or service unit outside the approved root was read or
modified. No privilege escalation or service restart was attempted.

Deployment cannot be fully validated within the explicit single-root scope:
both installed code trees, role configuration, public trust, TLS identity,
existing service bindings and quota enforcement must be inspectable before
deployment. No deployment or genuine signed live chain is claimed.

## Safe deployment requirements and decision log

1. Provide an authorized inspection/deployment scope covering both hosts'
   existing installed trees and public configuration/trust. Inspect only
   necessary non-secret fields; never expose keys, tokens or secret environment.
2. Verify exact source hashes and dependencies in broker and CEO/Manager/A/B/C
   installed trees; inspect existing service user, config and state bindings.
   Reuse services; do not create or enable new services.
3. Verify distinct pinned CEO/Manager/A/B/C public keys, matching signer public
   keys and role-scoped mTLS identities. New research must bind worker-a; the
   Manager decomposes A=worker-a, B=worker-b, C=worker-c, and C depends on A and B.
   The retired worker must remain denied at inference boundaries.
4. Verify the exact durable Owner-approved proposal/digest, signed handoff,
   unchanged primary workflow bindings, current limits and spending enforcement.
   No quota changes or repeat Owner approval within already approved bounds.
   A legacy workflow without an approved decomposition needs an authorized signed
   supervisory transition; no DB rewrite, migration or bootstrap retry bypass.
5. Back up protected runtime state without publishing it; deploy only the scoped
   validated source to existing targets with a reviewed rollback and verify
   installed hashes before allowing bounded internal research.
6. Collect genuine signed CEO → Manager → A/B → C → Manager evidence and the
   second research round under existing limits (three rounds, four Worker calls
   per round, twelve cumulative). Verify signatures, journal replay, assignment
   dependencies, provider provenance and all external/capital/MVP denials.
   Fixture results cannot substitute for this evidence.

Decision: source admission is implemented/tested and suitable for independent
code review. Withhold deployment and production acceptance until the above
installed alignment and scope prerequisites can be verified. No new services,
quota changes, Owner approval bypass, real CEO attachment, capital action, live
MVP execution or external venture activity was performed by this task.

Claude/GitHub review remains outstanding. Review handoff: the pushed commit
containing this report, the four scoped source/test files, and the evidence
directory. Review exact new-worker admission, distinct fixture keys, immutable
historical replay, Owner revocation and both expanded test results. Reviewers
must preserve the distinction between implemented, tested, pushed, deployed,
VM-verified and independently verified.
