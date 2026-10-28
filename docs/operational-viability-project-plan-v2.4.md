# Autonomous Venture Agent — Operational Viability Project and Implementation Plan
Version: 2.4 (consolidated owner-direction baseline)
Date: 2026-10-28
Repository: tobytuuby/Autonomous-Venture-Agent
Source baseline reviewed: main at 9523d5d25eeb91b0c5b1b06ebd828d913ff50f56
Status: Approved project direction documented; software readiness and execution contracts NOT yet certified.

## 1. Mission and acceptance

Create an autonomous business organization that evaluates opportunities, builds and validates usable online products, seeks owner approval for consequential external activity, and operates approved ventures with accountable finances and measurable profitability. Successful synthetic execution alone is not commercial viability. Do not expand infrastructure for its own sake.

**Mandatory hierarchy: Owner → AI CEO → Venture Manager → Specialized Worker.**
Work flows CEO → manager → workers; worker results and correction requests return to the manager; manager-reviewed results and premise concerns go to CEO; only required owner-level decisions go to owner. Technical brokers, schedulers, finance kernels, validators, monitors and recovery services transport, enforce and record decisions; they are NOT additional organizational authorities. All error paths, reviews, escalations, budgets and releases must preserve this chain. Never bypass a supervisory level as an optimization.

Role-model assignment is fixed: **CEO GPT-6 Sol; managers GPT-6 Sol; workers GPT-6 Luna.** Neither workers nor the system may escalate/substitute models without owner-approved policy change.

## 2. Responsibilities and approval boundaries

- **Owner:** sets the rules, approves initial external venture operating scope and seed capital, changes to authority/budgets/model policy, and exceptions; holds independent review and emergency stop power. No routine worker supervision or per-internal-task approval.
- **CEO (Venture-Control):** originates internal concepts, directs managers, judges completed manager-reviewed products and commercial cases, accepts/rejects/redirects strategy, and is the **financial governor** within owner-approved limits. No self-authorization of public launch, real outreach, or new/excess capital authority.
- **Venture manager (Venture-Agents):** creates/directs workers, plans and delegates work within CEO assignments, reviews/rejects/requests worker corrections, raises invalid premises to CEO, coordinates CEO-authorized venture operations. No direct owner or financial-policy bypass.
- **Workers (Venture-Agents):** research, build, test, and execute bounded assignments; report to manager only; cannot approve final output, change models, financial permissions, organizational roles or their own resource budgets.

**Standing internal preparation:** CEO may evaluate opportunities, direct manager/worker development, private staging, tests, internal research, iteration and abandonment within authenticated, bounded standing authority. A separately owner-signed preparation grant for every internal activity is NOT required. Identity signing and segregation of duties are still mandatory.

**External boundary:** owner discussion and durable approval of the exact venture proposal/version, scope, initial capital and external activities are required before launch/public release/customer outreach/real business commitments or payment initiation. After approval, CEO authorizes routine financial operations in scope, manager coordinates execution and workers implement assignments. Private preparation is not public launch.

**Existing policy reconciliation required:** Current repo `AGENTS.md` and `docs/owner-venture-approval-policy-v1.0.md` describe owner approval before *operational manager execution*. The owner's newer decision permits bounded **internal preparation** before owner approval but still denies external/financial authority. A narrowly scoped versioned policy correction and tests must reconcile this explicit conflict **before standing internal delegation is enabled**. Historical documents stay intact; until changed and verified, the existing runtime must remain fail-closed. This plan does not itself grant live authority.

## 3. Finances

Original guardrails: $1,000 total capital pool, no initial venture seed above $100, no cross-venture borrowing, 80% venture-usable/20% saved profit allocation, existing saved-$100 return threshold, and existing CEO 50% pool-reinvestment restriction. PayPal Business is the selected payment provider. CEO makes allocation/payment decisions, deterministic kernel enforces owner limits, payment adapter executes only authorized decisions and ledger reconciles cash/revenue/fees/refunds/chargebacks/expenses. AI operating overhead is separate from venture seed balances but included in economic profitability. No agent may raise its own authority or budgets.

AI compute governor must reserve and cap concurrent usage, per-task/worker/manager/venture and global daily/monthly spend, enforce timeouts/no uncontrolled retries, reconcile actual token costs, and deny exhaustion. Owner sets aggregate ceiling; CEO delegates bounded allowances via managers. No additional paid real-provider journey until effective controls and an approved spending allowance are verified.

## 4. Two-VM target and reuse

**Venture-Control:** CEO strategy and inference, registry, signing/trust, CEO delegation, audit, deterministic policy/kernel and cost enforcement, owner decisions, financial ledgers, shutdown. **Venture-Agents:** manager and worker inference, isolated research/development/testing, manager review and corrections, private staging/evidence. Reuse existing signed broker, durable queues, orchestration state machines, provider manager, identity, policy and finance code; don't recreate them.

Known recent reusable commits: `9523d5d` role model routing; `23e0fda` role signing; `a693603` provider-manager and CEO review; `f2c8e65` authenticated handoff; `2cfaf34` signed broker; `1b7d473` durable control plane; `38dc389` queue reconciliation; `15098cc` review state machine; `74fa2e2` online-product HTTP gates. Presence in source does not prove deployment. Existing unrelated dirty/untracked files must be preserved. No production/financial/external actions are authorized by this plan.

## 5. FOSS and external services

All newly selected/installed software must be **genuine FOSS with $0 software license and subscription spending**. Do NOT reject qualifying FOSS because it uses GPL, LGPL, AGPL, MPL, copyleft, network-use provisions or distribution obligations. Document package/version/license and material obligations; owner handles license-compliance decisions. Select packages for function, compatibility, reliability, security, maintenance and efficiency. Do not buy new software/cloud tooling.

**Four approved external-service exceptions:** (1) OpenAI inference, (2) PayPal processing, (3) GitHub repository/hosting collaboration, (4) existing LocalBridge/bridge infrastructure. These services themselves need not be FOSS; exceptions are confined to established purposes and existing cost arrangements. Any additional paid service needs owner approval. Never commit secrets or confidential runtime artifacts to GitHub.

## 6. Mandatory Phase 0 — Entire FOSS software stack READY before Release A

A historical repository "Phase 0" already exists for the policy kernel: this is a **new Operational Readiness Phase OR-0**, not a renaming or reopening of the certified historical P0.

Before implementation of Releases A–F, perform and complete these predefined readiness assignments, documenting all dependencies for **the entire planned lifecycle**:

- **OR0.1** Extract full-project software/runtime/test/integration requirements from repository code, manifests, source imports, scripts and releases A–F.
- **OR0.2** Inspect Venture-Control OS, Python packages, PostgreSQL, Git, cryptography, signing, broker, systemd, monitoring, backups, finance libraries and permissions.
- **OR0.3** Inspect Venture-Agents OS, Python/Node/npm, worker frameworks, isolation, HTTP application hosting, Chromium/Playwright, networking and test tools.
- **OR0.4** Verify FOSS status and inventory version/license/material obligations; record four service exceptions distinctly.
- **OR0.5** Produce a compatibility/versions and VM ownership matrix for all selected packages.
- **OR0.6** Before installing anything, produce **all** small sequential installation/configuration contracts for every missing package: target VM, version, prerequisites, permissions, exact actions, tests, rollback and owner sudo needs. Confirm no unreviewed surprises.
- **OR0.7** Install and locally smoke-test required control-side and agent-side runtimes and isolated dependency environments.
- **OR0.8** Install and smoke-test complete FOSS development/build/static-analysis/automated test stack.
- **OR0.9** Launch a real headless FOSS browser on Venture-Agents and exercise local HTTP forms, persistence and test-artifact output.
- **OR0.10** Smoke-test prerequisites for cross-VM auth/transport, web serving/TLS, databases, PayPal sandbox development (no payments), AI cost metering, monitoring and backups.
- **OR0.11** Run reproducible acceptance matrix on both VMs, resolve missing/incompatible software and verify restoration/install instructions.
- **OR0.12** Commit/push sanitized inventory, FOSS manifest, installation scripts, pinned versions, test evidence and a clear READY/NOT READY acceptance decision.

**Hard gate:** no A–F implementation until OR-0 is verified READY. All necessary software, including tools needed for later acceptance tests, must be installed and tested; source checkout alone is not readiness. Software prerequisites do not imply activation of real customer, payment or AI authority. If an unforeseen dependency later arises, stop the affected task, revise/readmit the readiness baseline with a separately predefined bounded task, then resume; never sneak an installation into an oversized Codex prompt.

## 7. Predefined sequential implementation releases (not authorization to execute)

**Release A — Two-VM runtime, 16 subtasks:**
A1.1 control inventory; A1.2 agents inventory; A1.3 source/deployment comparison; A1.4 VM ownership/migration map.
A2.1 manager dependencies; A2.2 package existing manager for agents VM; A2.3 deploy manager service; A2.4 deterministic execution/persistence test.
A3.1 worker contracts/isolation; A3.2 deploy worker runtime; A3.3 manager→worker assignments and returns; A3.4 review/correction integration.
A4.1 signed broker verification; A4.2 CEO→remote-manager handoff; A4.3 manager-reviewed result→CEO; A4.4 signed cross-VM rehearsal.

**Release B — Authority, role models and costs, 16 subtasks:**
B1.1 inventory existing grants; B1.2 reconcile versioned policy: internal preparation versus external approval; B1.3 implement authenticated standing internal delegation; B1.4 impersonation/replay/revocation tests.
B2.1 verify committed role-model routing; B2.2 configure on respective VMs; B2.3 enforce authenticated role mapping; B2.4 reject any substitution/switch.
B3.1 existing compute governance; B3.2 usage and actual-dollar accounting; B3.3 atomic concurrent cost reservations/hard ceilings; B3.4 exhaustion/cancellation/retry tests.
B4.1 recoverable queue review; B4.2 distributed recovery; B4.3 authorized suspension propagation; B4.4 fail-closed/hierarchy regression.

**Release C — Fully autonomous hierarchy, 16 subtasks:**
C1.1 CEO opportunity evaluation; C1.2 signed manager assignment; C1.3 durable lifecycle; C1.4 autonomous internal initiation.
C2.1 manager-directed specialist assignments; C2.2 worker evidence; C2.3 manager review/rework; C2.4 multiple improvement cycles.
C3.1 CEO accepts manager-reviewed outputs only; C3.2 approve/reject/revise; C3.3 premise rejection and CEO redirection; C3.4 replay-safe review history.
C4.1 complete owner review requirements; C4.2 finished product and business case package; C4.3 owner approve/reject/revise record; C4.4 external-action deny until exact approval.

**Release D — Functional online venture, 16 subtasks:**
D1.1 worker development capabilities; D1.2 bounded backend development; D1.3 persistence/auth; D1.4 private staging.
D2.1 isolated browser acceptance; D2.2 real customer journey; D2.3 reliability/security/persistence; D2.4 findings return to manager.
D3.1 research capability inventory; D3.2 approved public research; D3.3 market evidence/provenance; D3.4 demand/pricing/competition assessment.
D4.1 staging/release contract; D4.2 app isolation; D4.3 manager-coordinated, CEO-approved and owner-authorized public launch; D4.4 rollback/monitoring.
Studio Restock Kit is a **technical acceptance case**, not automatically authorized for commercial launch.

**Release E — Finance and resilience, 12 subtasks:**
E1.1 payment integration audit; E1.2 PayPal sandbox (no real capital); E1.3 reconciliation; E1.4 failure/refund tests.
E2.1 registry/limits; E2.2 CEO decisions/kernel authorization; E2.3 permitted adapter execution; E2.4 denial/exhaustion.
E3.1 owner-facing notifications; E3.2 backup code/config/state/evidence; E3.3 VM/database restore drill; E3.4 verify ledger/trust/hierarchy after restore.

**Release F — Independent acceptance and authorized pilot, 8 subtasks:**
F1.1 full deterministic CEO→manager→workers→manager→CEO journey; F1.2 browser/financial/security/failure tests; F1.3 P12 independent charter/review evidence; F1.4 actual independent P12 audit outcome.
F2.1 separate owner P13 scope authorization; F2.2 bounded real pilot; F2.3 measure customer usage/revenue/fees/AI cost/net results; F2.4 P14 post-test independent review.
P12 and P13 are distinct gates; no live authority is inferred from a green deterministic test.

## 8. Mandatory sizing / Codex contracts before execution

This is an initial task decomposition, **not permission to give Codex broad prompts**. Before the first Codex prompt of **each release**, inspect actual code and fully size *all* tasks of that release. If any listed subtask remains too large, subdivide it in the authoritative plan into separately numbered sequential contracts **before the first prompt of that subtask**. Do not discover prompt size through retries or timeouts, expand active prompts, or silently add unrelated work.

Every contract must provide: single objective, organizational authority/implementer/reviewer, source files/components, exclusions, prerequisites, verified OR-0 software, expected change set, focused and regression tests, security/finance/hierarchy checks, VM deployment target, acceptance evidence, rollback, and GitHub review artifact. Fixed role-model and adjacent-level delegation apply to all agent work. Unplanned discoveries require a recorded plan adjustment before issuing another prompt.

## 9. Mandatory GitHub-first transparency and independent Claude review

**Claude has GitHub access for review but does NOT have LocalBridge or VM access. GitHub is the authoritative shared review record.**

- **Every change must be committed and pushed:** project plans, phase contracts, policies, source, tests, FOSS inventory, setup/deployment scripts, sanitized config templates, verification evidence, and review reports. No completed work may exist only as an unpushed VM modification. Do not stage unrelated pre-existing changes.
- **Persistent VM configuration is reproducible from Git:** track templates, declarative settings, installation/deploy scripts and exact approved manual commands (never secrets or sensitive server state). Reconcile any necessary emergency drift back to Git immediately.
- **Evidence is independently reviewable:** store sanitized test commands, exit codes, summaries, relevant logs, hashes, source commit, deployed VM revision/identity, deployment command, verification outcome, and limitations. Do NOT check in live credentials, tokens, private keys, customer data, private runtime DBs, unrestricted logs or sensitive machine metadata. Reference protected evidence by stable digest and access method where it cannot safely be published.
- **Explicit evidence classes:** implemented ≠ tested ≠ pushed ≠ deployed ≠ VM-verified ≠ independently verified. Claude can inspect repo changes/reproduce accessible tests, but GitHub evidence alone is not direct independent proof of VM state.
- **Claude handoff per task/release:** GitHub URL/path + exact commit, change scope, applicable policies, test/evidence locations, deployment assertions and limitations, known risks and pointed review questions. Claude findings are reviewed against code and requirements; neither assistant nor Claude independently alters owner-defined authority.
- **Completion chain:** implement → test → **commit and push source** → deploy → verify actual runtime → **commit and push sanitized deployment/verification evidence**. Changes from deployment defects follow the same chain. For documentation-only work: edit → validate → commit → push; no fake deployment claims.
- Report pushed commit(s), evidence, and any unverified claims; a dirty unrelated worktree must remain preserved.

## 10. Owner sudo command format

Whenever owner action on a VM requires sudo: identify VM and purpose, and put **each individual sudo command in its own separate fenced code block**, without pasted prompts/output, combined chains or extraneous text. Reference this section whenever giving VM instructions. Prefer authorized bridges for routine work. Never ask the owner to paste credentials/keys into chat.

## 11. Validation and gates

Every implementation task: read plan and governing policy; verify HEAD/branch/remote/worktree; inspect reuse; verify OR-0 baseline; execute bounded contract; run focused/regression/security/hierarchy tests; commit/push; deploy correct VM; independently check actual runtime; commit/push sanitized evidence; present Claude review handoff. No provider-backed paid execution without confirmed spending enforcement and bounded owner-approved AI allowance.

Gates: OR-0 FOSS stack READY; A two-VM hierarchy; B authenticated standing authority + hard costs; C autonomous review; D independently tested working online product; E CEO-governed transactions and recovery; F P12 audit + separately authorized P13 real pilot + P14 review.

**Non-goals:** additional VM, new orchestration platform, second financial provider/governor, new approval layers, worker→CEO bypass, automatic model escalation, paid software, unnecessary dashboards, wholesale rebuilding of existing components.

## 12. Next step and auditability

Begin **OR0.1** only after preserving existing dirty worktree and confirming authoritative source/docs. Perform whole-lifecycle inventory, then predefine ALL OR-0 installation steps prior to installation. No Release A implementation until software gate READY. This plan's existence does not prove readiness or authorize real operations.

This plan version is deliberately distinct from `project-phase-plan-v2.3.md`, the existing historical project phase map. Existing phase evidence and policy remain intact until explicit, versioned reconciliation.
