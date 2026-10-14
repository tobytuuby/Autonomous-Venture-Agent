# Core Synthetic Orchestration — Focused Plan

**Version:** 1.0
**Status:** Draft for user review
**Repository baseline inspected:** main at 37c393d7723ee8bbe4bc276a435d912c6b621136
**Execution class:** Offline synthetic fixtures only
**Phase mapping:** This is a core capability plan, not a numbered roadmap phase. It does not alter P12–P14 status or authorize later phases.
**Operating-policy draft:** [`venture-operating-policy-v1.0-DRAFT.md`](venture-operating-policy-v1.0-DRAFT.md) records the intended venture funding and profit rules, without granting runtime authority.

## Purpose

Connect the existing CEO shadow, P6.1 coordination records, and P7.5 worker boundary concepts into one useful synthetic flow:

1. The CEO proposes one venture idea.
2. A manager receives it and creates bounded work packets.
3. Synthetic workers process only supplied synthetic inputs and return results.
4. The manager aggregates results.
5. The CEO presents an advisory recommendation and result artifacts for human review.

The purpose is to exercise orchestration end to end. Recorded coordination/admission/task data alone does not constitute agent creation, dispatch, or work execution.

## Current implementation distinction

At the inspected baseline:

- agents/ceo/agent.py records shadow decisions and proposed tool calls. It does not instantiate or dispatch a manager.
- kernel/p6/coordination.py validates and records effect-free coordination packets. It does not deliver packets to a running actor.
- kernel/p7/worker_boundary.py records synthetic worker admission and task data. Its module documentation says it does not create or dispatch workers.
- The existing provider adapter can make a network request when configured. It is outside this plan and must not be invoked by the synthetic flow.

The implementation associated with this plan is currently an uncommitted offline harness in kernel/synthetic_orchestration.py, with tests in tests/test_synthetic_orchestration.py. It uses deterministic local role fixtures and workers; it does not perform model inference or create separate agent processes.

## Focused scope

- One proposal and one synthetic venture identity per flow.
- A deterministic CEO role fixture emits one structured idea.
- A deterministic manager role fixture creates at most three typed work packets.
- A fixed allowlist of in-process worker functions processes bounded synthetic inputs.
- The manager aggregates worker outputs and hashes result records.
- The CEO produces a fixed advisory review package containing the proposal, recommendation basis, and JSON artifacts.
- Each flow record labels its synthetic execution class, taint/provenance, and zero-effect boundary.

## Non-goals

- Real CEO attachment, live model/provider calls, or external data retrieval.
- OS-level agent/process creation, arbitrary dispatch, queues, shell, browser, or tool execution.
- Live venture launch, worker authority, credentials, network access, customer contact, spending, money movement, publishing, deployment, or other external effects.
- A production-ready orchestration framework, autonomous business decision, or acceptance of any phase gate.
- Any change to P12, P13, or P14 authorization or status.

## Architecture and trust boundaries

The flow is an in-process coordinator over plain JSON-compatible data:

1. **Offline CEO fixture:** emits a proposal with a venture ID, title, problem, and hypothesis.
2. **Proposal validation:** enforces exact fields and bounded identifiers/text. The proposal remains untrusted and tainted.
3. **Offline manager fixture:** receives the proposal and emits bounded packets. The packet schema permits only a fixed worker type, task identity, objective, title, and typed synthetic inputs.
4. **Synthetic workers:** a closed registry supports evidence listing, arithmetic over finite numbers, and checklist preparation. Workers have no provider, network, filesystem, credential, subprocess, or queue interface.
5. **Manager aggregation:** binds results to task and venture identities and hashes each result.
6. **CEO review package:** returns a fixed advisory recommendation and in-memory JSON artifacts for human review.

Model-generated or model-shaped content is data only. It cannot grant authority, approve an action, alter the fixed worker registry, or change the review disposition. Unexpected fields fail validation. Instruction-like text may remain visible as content, but is never interpreted as executable instruction. The harness sets every repository-defined live-authority field false and records no execution or external action.

## Implementation increments

1. **Contracts and limits:** define proposal, assignment, task, result, aggregate, and review-package shapes; set text, input-size, and task-count limits.
2. **CEO-to-manager handoff:** validate one proposal and construct a scoped assignment record.
3. **Bounded manager planning:** validate unique task IDs, supported worker types, and typed input data.
4. **Synthetic worker execution:** run only allowlisted local functions and produce JSON artifacts.
5. **Aggregation and review:** verify task/result binding, hash results, and create the human-review package.
6. **End-to-end verification:** test normal flow, hostile content, malformed inputs, authority invariants, and repository regression.

## Risks and controls

| Risk | Control |
|---|---|
| A recorded proposal or assignment is mistaken for a real launch or dispatch | Use explicit synthetic statuses and zero-execution indicators; no launch or dispatch adapter exists in this module |
| Model text is treated as authorization | Keep generated content tainted; accept only exact data shapes; keep recommendation fixed and advisory |
| Manager tasks exceed intended bounds | Enforce a three-packet maximum, bounded text and input size, unique task IDs, and a closed worker allowlist |
| Worker result is attached to the wrong venture or task | Include task and venture IDs in each result and artifact; aggregate only results produced from the validated packet list |
| Synthetic evidence is mistaken for real agent behavior | State that roles are deterministic fixtures and workers are in-process functions; make no inference about provider, process, or production behavior |

## Tests and evidence

Required verification for this scope:

- End-to-end synthetic flow produces one proposal, a manager assignment, bounded tasks, worker results, an aggregate, and a review package with artifacts.
- Every output stage carries all nine repository-defined authority flags as false, synthetic_only=true, effect=none, execution_performed=false, and external_action_count=0.
- Instruction-like text does not change the fixed review recommendation or enable an action.
- Unexpected authority fields, invalid worker types, malformed/non-finite worker inputs, excessive task count, duplicate IDs, oversized records, and invalid identifiers are rejected.
- Test output reports the exact focused and full-suite denominators.
- Source review confirms the module has no provider, network, credential, filesystem, subprocess, or queue integration.

Recorded implementation evidence at draft creation: focused suite 6/6; full repository suite 618/618; Python compilation succeeded. These are execution results for the current working tree, not an independent acceptance decision.

## Review boundary

This draft documents a bounded synthetic implementation only. It is not a phase entry decision, a certification, production readiness evidence, or authorization for any later phase or external action. The user remains the final reviewer and decision-maker.
