# MCP Tool Evaluation for the Autonomous Venture Agent

**Status:** Developer workflow decision record  
**Date:** 2026-09-15  
**Authority:** Phase 0 v9 architecture and implementation plan v3.0 remain frozen and authoritative.

## Decision

No generic MCP tool is approved for placement in a venture agent's toolset during Phase 0.

The CEO, Venture Manager, Scout, and worker roles may receive only the frozen, broker-mediated capability-call schemas. Generic browser, shell, filesystem, search, credential, or unrestricted agent-creation tools must not be exposed to the model. This decision does not prohibit a developer from using documentation or research tools while implementing the system.

## Tool assessment

| Tool | Phase 0 disposition | Reason |
|---|---|---|
| Context7 | Use selectively for developer work | Useful for version-sensitive OPA/Rego, OpenBao, and framework documentation. It is not runtime agent authority. |
| Exa/Brave Search | Do not add | Redundant with available developer web research and not an agent capability. |
| Supabase MCP | Do not add | The infrastructure plan uses self-hosted PostgreSQL rather than Supabase. |
| Cloudflare/Vercel MCP | Do not add | The planned topology uses self-owned VMs and reverse-proxy infrastructure, not managed edge/serverless deployment. |
| Chrome DevTools MCP | Defer | Phase 0 has no browser-facing application surface to validate. |
| Playwright MCP | Defer | Phase 0 certification is API/process-level: policy tests, broker tests, fail-closed tests, and the adversarial suite. |

## Security interpretation

The security boundary is application-enforced authorization, not a framework's default tool list. A framework may be used later only when:

1. The model receives an explicitly allowlisted set of broker-wrapper tools.
2. Each wrapper maps to a frozen capability-call schema.
3. Identity, authorization, spending limits, audit records, provenance, and fail-closed behavior remain controlled by the kernel and broker.
4. Generic framework tools are disabled rather than merely discouraged by prompts.
5. Shadow or test execution precedes any real-world side effect.

A research tool must not be added to an agent simply because it is useful. The agent's tool list must be reviewed as part of the configuration fingerprint and certification evidence.

## Timing

This is not a Phase 0 architecture change. It is a developer-tooling decision that can be revisited when a later phase introduces a browser-facing operator surface or a documented need for another external integration.

## References

- [Phase 0 policy-kernel specification v9](../phase0-policy-kernel-spec-v9.md)
- [Phase 0 implementation plan v3.0](../phase0-implementation-plan.md)
- [CrewAI search and research tools](https://docs.crewai.com/v1.15.6/en/tools/search-research/overview)
- [Claude permission policies](https://platform.claude.com/docs/en/managed-agents/permission-policies)
- [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
