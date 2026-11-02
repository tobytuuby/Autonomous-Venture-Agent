# CEO recommendation structural recovery v1.0 — 2026-11-02

Base: af2340eefab4e2d07fc96dae82de7cce1d63cdd4, main.

## Change and decision semantics

The existing review path now decodes an exact recognized enum or that enum
followed by ": " and a nonempty single-line explanation. Exactly one occurrence
of a recognized enum must appear in the recommendation. Unknown, malformed,
prefixed, multiline and ambiguous values fail closed. Only the recommendation
wire encoding is decoded; assessment, evidence_gaps and next_internal_task are
unchanged. The original strict JSON, round eligibility, field lengths, signed
artifact attribution, criteria, authority and quota checks remain unchanged.
A round-three READY_FOR_OWNER_DISCUSSION still fails; it is never silently
changed to PROCEED_TO_MVP. No mandatory Owner approval gate is introduced.

Before parsing, the exact provider response (including the verbatim JSON content
string) and original PENDING checkpoint are stored beside the existing review in
a create-once .provider-intent.json local artifact. Creation uses a flushed
temporary file, exclusive hard link, mode 0400 and directory fsync. Existing
intents must match byte-for-byte and cannot be replaced through this path.
A symlink is denied. This is application-level immutability, not protection
against privileged filesystem tampering. The signed packet binds the canonical
provider envelope hash. Historical COMPLETE packets retain their original bytes
and behavior. The original inference database remains read-only during recovery;
no reservation, paid retry, new research round or quota reset is introduced.

Invalid assessments retain their PENDING checkpoint and original saved response.
No speculative repair or fabricated criterion is supplied. Any additional
schema repair requires examining the actual saved response and proving that
the original existing provider mechanism can safely perform the bounded repair.
This change neither bypasses that requirement nor introduces a repair provider.

## Validation and provenance

Command: python3 -B tests/acceptance-evidence/ceo-recommendation-parser-20261102/validate.py

The script archives HEAD into artifacts/ceo-recommendation-parser-clean and
overlays only the three scoped implementation/test files. It confines test
temporary files to the project root and excludes unrelated dirty code.

- Focused: 37 tests, all passed, exit 0, 2.927 seconds.
- Regression: 135 tests, all passed, exit 0, 26.659 seconds.
- git diff --check: exit 0.
- Raw per-test reports: focused.log and regression.log; exact exit files beside them.
- Existing ResourceWarnings about unclosed fixture databases are retained in the
  regression report; they did not fail the test run.
- Bridge process: proc_mvzkth64_gons9g, PID 3704417, polled to exited.
  Bridge log metadata: /home/epsilon/.chatgpt2localbridge/process-logs/proc_mvzkth64_gons9g.log.
  The completed redirected validation.log was read through venture-control inside
  the approved root; the external bridge log was not opened.

Coverage includes exact/colon enums, malformed/ambiguous values, unchanged content,
signature verification, immutable original checkpoint and response, crash/replay
idempotence, ledger byte preservation, immutable-intent mismatch/symlink denial,
invalid evidence remaining PENDING, unchanged round-three eligibility, and the
real signed workflow verifier/journal for positive round-two/three dispositions.
The integration test retains cumulative rounds and verifies the journal;
it does not roll back signed state or restart a terminal disposition.

Evidence class: independently observed local isolated software tests using
fixtures/mocks. This is not production acceptance or independent model execution
verification. ADV-001–ADV-049 and the /49 denominator are unchanged.
Independent GitHub/Claude review has not been obtained in this task.

## Production blocker and operator impact

The Owner reports research-4e6018e70bf43a549e289b3f at HOLD with a durable
PENDING CEO response. The supplied recommendation has the supported structural
encoding. The full response, request, installed checkpoint, signature, retained
consumption and current workflow have not been independently verified here.

The final task instruction restricts operations to
/home/epsilon/venture-control-workspace. The installed checkpoint supplied in
the task is /usr/local/lib/venture-ceo-level2c/artifacts/level2c-ceo-r4/run5/research/research-reviews/research-4e6018e70bf43a549e289b3f.json;
the canonical scoped research-review-inference.sqlite is also outside the
approved root. Permission to inspect and update the existing installation and
verify its existing CTKFamily publication was requested; no response has arrived
at the time of this report. Elapsed time is not approval.

Consequently deployment, service restart, actual response validation/repair,
production signed disposition and CTKFamily propagation remain OPEN. No PASS
is claimed for those actions. Remaining risks include additional unseen schema
violations, changed signed state/request/policy, exhausted existing provider
allowance or an unavailable authorized publication/transition path.

Accept this as a tested source correction only. Once installation access is
authorized, preserve and validate the original scoped response/checkpoint,
check every unchanged safeguard, and inspect any exact remaining error before
considering bounded repair through the existing provider mechanism. Preserve
positive CEO semantics and Task03's no-repeat-Owner-checkpoint rule for
already-authorized internal MVP work; do not infer an execution grant or renew
research quota.

No real CEO attachment or activation, production deployment, provider call,
capital, payment, launch, customer contact, signed-history rewrite or CTKFamily
mutation was performed. Unrelated dirty files remain outside the change.
