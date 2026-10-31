# Task 01 Production Verification — 2026-10-31

Read-only inventory of Venture-Control, Venture-Agents and CTKFamily.

GitHub main and Control checkout: 1f067e3. Control checkout has 47 outstanding worktree entries; preserved. CTKFamily checkout: 0c595c5 with 42 outstanding entries; preserved. Agents workspace is not a Git checkout.

Verified active: Control owner API, idea review, mTLS broker; Agents Level2D manager, three workers, research manager and research worker. Active services alone do not establish successful end-to-end execution.

Agents installed worker_inference differs from source checkout: installed 0af215e054b8 versus source a35542ba4f99. A read-only diff shows installed policy accepts actor_id while source supports bounded actor_ids for worker-a/b/c, plus altered authorization and reservation logic. This is deployment version drift; it is not evidence of an active exploit or failure.

Worker inference reservations use workflow_id plus assignment_id plus identity, with four-call ceilings per assignment and workflow. Provider reservation limits calls per session and uses shared daily provider quota (94 requests). Neither proves a per-venture cumulative inference quota across distinct research workflows. Unique workflow IDs cannot be adopted as quota-reset policy without fixing that gap.

CEO research review emits NEEDS_MORE_RESEARCH or READY_FOR_OWNER_DISCUSSION, but signed three-round continuation/terminal decisions were not demonstrated. Workflow remains PREPARATION_ONLY. Research approval is not launch/capital approval.

CTKFamily owner page uses GET /v1/owner/ideas and review POST /v1/owner/reviews. It renders Awaiting renewed scope/authorization for NEEDS_MORE_RESEARCH; its documented one-review-per-proposal flow has no continuation action, contradicting newer Owner policy permitting bounded autonomous continuation. Existing PHP venture_ideas contract tests passed.

Implementation decision: reuse existing signed CEO decision and workflow, existing reservation and ledger, and existing owner ideas API/page. Task02 must explicitly enforce per-venture three-round maximum and durable cross-workflow cumulative financial allowance, with idempotency/replay tests. Task03 must force READY_FOR_OWNER_REVIEW or REJECT_OR_DEFER when round limit is reached; never auto-launch. Task04 extends existing endpoint and page; no new service justified.

Outstanding boundaries: no authenticated live website request using Owner credentials performed; no claim of current ledger financial balance or historical signature verification; real payments not verified. These limitations are documented evidence, not invented acceptance.

No business-state mutations or privilege changes were made. This task is documentation-only, so deployment of new services is inapplicable.
