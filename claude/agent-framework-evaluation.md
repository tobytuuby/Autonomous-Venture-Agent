# Agent Framework Evaluation

**Status:** Candidate-screening decision record  
**Date:** 2026-09-15  
**Authority:** Phase 0 v9 architecture and implementation plan v3.0 remain frozen and authoritative.

## Decision

Do not select an agent framework during P0.0. The framework choice belongs to the later CEO/Venture Manager/worker implementation work. Any eventual framework is subordinate to the policy kernel, broker, ledger, governors, identity model, and recovery design.

The selection criterion is not whether a framework advertises multi-agent features. It is whether the application can enforce an exact allowlist of broker-mediated capability wrappers and keep all authoritative state outside the model runtime.

## Candidate assessment

| Candidate | Assessment |
|---|---|
| Pydantic AI | Strong candidate for typed, explicit tool wrappers. Still requires application-level allowlisting, identity binding, audit, and fail-closed enforcement. |
| Claude Agent SDK | Potential candidate where its execution model and deployment constraints fit. Do not assume SDK defaults are the security boundary; application-controlled custom tools require explicit enforcement. |
| CrewAI | Viable only under a strict wrapper-and-allowlist design. Its search, research, coding, and other integrations make accidental privilege expansion easy, but those tools are added by the application rather than proving that every agent receives them automatically. |
| LangGraph | Viable for orchestration and stateful workflows, but requires a deliberate integration with the committed Postgres job-queue, heartbeat, reclaim, idempotency, and recovery model. Its checkpoint/store model must not become a second authoritative state system. |
| n8n | Keep in its existing scheduling/housekeeping role. Do not use it as the reasoning-agent tool plane unless a later design decision explicitly establishes the required controls. |
| Flowise/Base44 | Not suitable for the Phase 0 agent runtime because visual composition increases the risk of casually attaching generic tools. |
| Cursor/Claude Code | Developer workflow tools only; never runtime capabilities for venture agents. |

## Required constraints for any future choice

The selected framework must satisfy all of the following:

- Agent tool lists contain only the frozen broker-mediated capability schemas.
- No direct shell, filesystem, browser, search, credentials, payment, deployment, or unrestricted spawning tools reach the model.
- The broker revalidates identity, scope, budgets, provenance, plans, and action graphs.
- Durable jobs, heartbeats, reclaim, idempotency, and recovery remain governed by the project design.
- The ledger and policy kernel remain authoritative; framework memory and checkpoints are not authoritative financial or policy state.
- The first real CEO runs in shadow mode, with decisions logged and no external side effects.
- The configuration is inspected and included in certification evidence before Stage 1 is considered.

## Final disposition

This record narrows the future decision; it does not choose CrewAI, Pydantic AI, Claude Agent SDK, or LangGraph now. No architecture or implementation-plan edit is authorized by this record.

## References

- [Phase 0 policy-kernel specification v9](../phase0-policy-kernel-spec-v9.md)
- [Phase 0 implementation plan v3.0](../phase0-implementation-plan.md)
- [Pydantic AI tools](https://ai.pydantic.dev/tools/)
- [CrewAI tools](https://docs.crewai.com/v1.15.6/en/tools/search-research/overview)
- [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- [Claude permission policies](https://platform.claude.com/docs/en/managed-agents/permission-policies)


---

## Extension: additional framework candidates

This extension records additional candidates screened against the same frozen boundary. It does not amend the architecture or implementation plan.

### Candidate findings

- **Mastra** is a TypeScript-native option and therefore a stack mismatch for the current Python/self-hosted direction. Its memory facilities would also need to remain non-authoritative. This is a fit and sequencing concern, not an architecture prohibition.
- **Dify** is a visual LLM application platform. It is not selected for the secured runtime because visual composition and one-click deployment make accidental attachment of generic tools more likely.
- **OpenAI Agents SDK** is a strong Python candidate for explicit tools, handoffs, guardrails, and lightweight orchestration. Its MCP, sandbox, shell, filesystem, and other capabilities must not be enabled for venture agents unless separately authorized by the kernel design.
- **Claude Agent SDK** remains a candidate when Claude is selected. Computer-use capabilities are optional, but they must be excluded explicitly and verified absent from every venture-agent configuration.
- **LlamaIndex Workflows** and **Haystack** are better-shaped candidates for a bounded Scout evidence/retrieval subsystem than for CEO or Venture Manager orchestration. They are not inherently capability-less: both can support agents or expose pipelines as callable tools. Scout must therefore remain evidence-only, with provenance and taint metadata preserved and all data access bounded outside the model's discretion.
- **Microsoft Agent Framework** and **Google Vertex AI Agent Builder** are not selected for the current self-hosted, kernel-controlled design because their managed platform assumptions do not match the committed topology and trust boundary.

### Revised ranking

1. OpenAI Agents SDK or Pydantic AI for the future CEO/orchestration layer.
2. LlamaIndex or Haystack for a bounded Scout evidence/retrieval subsystem.
3. LangGraph if its persistence is explicitly subordinated to the Postgres durability model.
4. CrewAI or Claude Agent SDK only with the same strict wrapper and allowlist controls.

### Required interpretation

Explicit tool configuration is useful but is not itself a security control. The enforceable controls remain:

- broker allowlisting;
- broker-side identity and authorization checks;
- no direct shell, browser, filesystem, search, credential, payment, deployment, or unrestricted spawning tools;
- Postgres and the kernel remaining authoritative;
- shadow-mode CEO operation before external effects;
- configuration fingerprint and tool-list inspection before P0.15 certification.

This extension does not select a framework and does not authorize a P0.0 architecture or implementation-plan change.
