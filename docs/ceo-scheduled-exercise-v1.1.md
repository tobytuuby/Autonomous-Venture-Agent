# Scheduled advisory queue — operator guide v1.1

This implementation advances bounded advisory assignments through the existing
hourly `agents.ceo.scheduled_exercise` entry point. It supersedes the static
scheduling behavior described in v1.0, retained as historical implementation
evidence. It changes no policy gate, phase approval, live authority or ADV /49
denominator.

The original synthetic bootstrap is retained and durably reconstructed on every
tick, including its configuration fingerprint and decision chain. An empty state
directory permits at most three bootstrap provider calls and does no queue work
on that invocation. Existing completed state can seed one CEO-generated next
assignment from its completed review. Shelving produces no assignment.

Queue cycles use UTC calendar hours. One completed queue cycle per hour is
permitted. Repeated starts in that hour return QUEUE_REPLAYED with zero provider
calls. A later hour executes at most one pending assignment: a model manager
drafts content into two packets, the existing local summarize_evidence and
checklist workers produce an aggregate, and a model CEO reviews that aggregate
and supplies either one successor assignment or null to stop. A successor never
executes within the cycle that created it. The queue has at most one pending item.
There are at most two API dispatches per queue invocation; seeding needs one.
There are no provider retries, fallback fixtures, tools or business action adapters.
The existing service timeout is 180 seconds; provider timeout is 30 seconds.

The service-owned state directory gains queue.started.json, queue.sqlite,
queue.decisions.sqlite and queue.decisions.jsonl. The original report and
workflow databases stay in place. Queue item IDs are assigned locally; each item
has its parent, bounded title/objective, QUEUED or COMPLETED status, and completed
manager/worker/review result. SQLite cycles record STARTED/COMPLETED status and
durably reserve each dispatch before the network call. CEOAgent retains raw
role decisions and event lineage. Completion, successor creation, work signature
and cycle acknowledgement share one SQLite transaction. The fsynced start marker
prevents a missing queue database from silently starting over.

A STARTED cycle blocks subsequent inference even after the hour changes.
Interrupted calls, invalid responses, failed review hashes and repeated objectives
therefore require operator investigation. No automatic reset or retry switch is
provided. The prior report and queue completion state are preserved on failure;
status.json records the latest outcome. A crash after queue commit but before
status/report publication replays the committed cycle without another dispatch.
The gate and provider configuration are checked on every invocation, including
replay; changes to the provider fingerprint deny continuation.

Normalized objective identity rejects identical objectives across all history.
Identical completed worker type/input packets are also rejected even if task IDs
or assignment labels change. Recent assignments (up to 20) are supplied to the
CEO to discourage paraphrased repetition. Semantic equivalence cannot be proven:
paraphrases and low-value drafts may still pass. The manager is instructed to
produce actual offline draft content, but automated checks establish bounds,
shape and lineage, not business quality or truth.

The existing linked systemd service reads this project code directly, so no unit
replacement, credential copy or new service is needed. Continue using the
existing protected environment files and legitimate runtime gate. Neither is
modified. Do not delete state to force progress. Inspect status and queue records
through the existing service/operator permissions. A normal oneshot returns to
inactive with Result=success and ExecMainStatus=0; the timer remains waiting.
QUEUE_DENIED/QUEUE_BLOCKED requires investigation, not enabling live authorities.

Evidence from fixture tests is synthetic local execution only. Real configured
provider responses remain configured_provider_response_not_independently_verified:
successful HTTPS calls and validated content do not independently establish
remote model identity, billing or provider isolation. All work stays advisory,
hypothetical, and synthetic-only. No payment, capital, customer contact, publishing,
deployment or live CEO attachment is available. Growth of durable history is
unbounded over time; there is no global spend budget or automatic archival.
