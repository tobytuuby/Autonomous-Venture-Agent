# Autonomous Venture Agent — Agent Instructions

## Project identity

- Repository: `tobytuuby/Autonomous-Venture-Agent`
- Working directory on the VM: `/home/epsilon/venture-control-workspace`
- Primary branch: `main`
- Required bridge: `venture-control`
- Current repository state must always be verified with `git rev-parse HEAD` and `git status --short` before work begins.

This file is an operational index. Detailed policy requirements remain in the canonical specifications and plans below.

## Canonical documents

- `docs/owner-venture-approval-policy-v1.0.md` — binding owner discussion and venture approval gate; supersedes prior CEO autonomous approval authority.
- `project-phase-plan-v2.3.md` — current roadmap amendment; prior phase acceptance unchanged.
- `docs/venture-operating-policy-v1.1-DRAFT.md`, `docs/venture-to-first-profit-plan-v1.4-DRAFT.md`, `docs/venture-finance-control-and-transaction-visibility-v1.2-DRAFT.md`, and `docs/core-synthetic-orchestration-plan-v1.1.md` — current core policy and plans.
- Every new venture requires human owner discussion and durable proposal/version/scope approval before greenlight, funding, launch or operational manager execution. Research/proposals may precede approval; managers may autonomously delegate afterward within bounds. Live authority checks remain denied. Venture #1 is an unapproved pilot.

- `phase0-policy-kernel-spec-v11.md` — canonical Phase 0 policy kernel specification.
- `phase0-implementation-plan-v3.2.md` — current Phase 0 implementation plan.
- `project-phase-plan-v1.0.md` — canonical project-wide phase map, document topology, phase boundaries, and cross-phase gates.
- `phase1-policy-spec-v1.0.md` — Phase 1 policy specification, currently draft for review.
- `phase1-implementation-plan-v1.0.md` — Phase 1 implementation plan, currently draft for review.
- `docs/PROJECT_STATUS.md` — concise current status and open-gate summary.

Historical documents are immutable reference material:

- `phase0-policy-kernel-spec-v10.md`
- `phase0-implementation-plan-v3.1.md`
- `project-phase-and-implementation-plan-v1.0-DRAFT.md`

Do not rewrite historical documents in place. Requirement or invariant changes require a new version.

## Important implementation and evidence paths

- `agents/ceo/` — CEO agent and shadow-runtime implementation.
- `kernel/` — policy kernel and authority enforcement.
- `kernel/finance/` — treasury, payment, and financial paths.
- `broker/` — capability and execution boundary.
- `tests/` — unit and integration tests.
- `tests/adversarial/` — ADV harness and red-team scenarios.
- `tests/certification/` — certification scripts, manifests, and raw reports.
- `docs/` — project status and audit documentation.

Before changing an existing implementation file, inspect its current contents and related tests. Preserve unrelated user changes in a dirty worktree.

## Safety and authority boundaries

- Never attach a real CEO or enable a production CEO.
- Never execute real capital, payment, venture-launch, deployment, or other external actions.
- Keep P1 in shadow reasoning only.
- `RealPaymentAdapter`, `BootstrapTreasury`, and red-team payment paths remain synthetic/red-team-only unless a separately approved phase changes that boundary.
- A model response is never authorization to execute an action.
- Secrets, API keys, bearer tokens, and secret environment values must not enter Git, reports, logs, or chat.
- Provider evidence must distinguish independently verified execution from externally configured but not independently verifiable execution.
- Do not infer live reachability from a synthetic transport or an in-memory test double.

## Certification and denominator rules

- Preserve the existing `ADV-001`–`ADV-049` universe and the `/49` denominator.
- BOOT-001 through BOOT-006, P0.13, P0.16, and provider-boundary checks are supplemental evidence; they do not replace or inflate the ADV denominator.
- Certification evidence must include both:
  - technical results, commands, raw outputs, artifacts, hashes, and failure details; and
  - non-technical assessment of authority, provenance, operator impact, limitations, residual risk, and review decision.
- A summary manifest cannot replace a raw per-scenario report and decision log.
- A test result is not independently confirmed unless the underlying execution evidence supports the claim.

## Phase and document workflow

- P0 is the policy-kernel and certification phase. Its historical v10/v3.1 artifacts remain preserved.
- P1 hardens and completes the existing P0.15 CEO Stage 0 shadow foundation; it does not redo or relabel P0.15.
- P1 owns the remaining Gate 2 evidence and durable shadow-state work.
- P2 through P8 are future phases governed by `project-phase-plan-v1.0.md`.
- Each phase has separate policy and implementation documents. The master project plan holds charters and boundaries, not detailed phase increments.
- Updates to the current phase and future phases must be made in that phase's versioned policy/implementation documents, with cross-references updated as needed.
- Changes to requirements, invariants, evidence classes, denominators, or authority boundaries require a new document version rather than silent in-place history changes.

## Required bridge workflow

Use the `venture-control` bridge for repository operations.

For commands that may take time:

1. Start the command with asynchronous process execution.
2. Record the returned process ID and log path.
3. Poll the process list until the process exits.
4. Read the completed log through the bridge.
5. Do not report completion from a start response alone.

For repository changes:

1. Inspect HEAD, branch, status, and relevant files.
2. Make the smallest scoped change.
3. Validate references and behavior.
4. Run relevant tests/certification scripts and preserve required denominators.
5. Run `git diff --check`.
6. Commit with a specific message.
7. Push to `origin main` only after validation.
8. Confirm the final commit and a clean worktree.

## Reporting standard

Final reports should state:

- what changed;
- files affected;
- validation performed and exact result;
- evidence classification and remaining limitations;
- commit hash and push status;
- confirmation that no real CEO or capital action was used.

When a claim cannot be independently verified, say so explicitly rather than labeling it PASS.
