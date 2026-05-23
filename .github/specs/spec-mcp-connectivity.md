# MCP Connectivity Specification

**v2.0.0 | purpose_driven_agent._aos_mcp_servers**

---

## Identity

MCP client primitives encapsulated within `purpose_driven_agent._aos_mcp_servers`. All downstream CXO agents inherit MCP connectivity through `PurposeDrivenAgent` method calls — no downstream layer imports `_aos_mcp_servers` directly. The MCP interface boundary is `PurposeDrivenAgent`.

Whitepaper: `boardroom-whitepaper-v4.md` §4.2 — Standard MCP Servers

---

## Encapsulation Contract

`_aos_mcp_servers` is a private subpackage. It is:
- Not in `__all__`
- Not importable as `aos_mcp_servers` (top-level)
- Not imported by any downstream layer (`leadership-agent`, `business-agent`, CXO agents)
- Accessible only as `purpose_driven_agent._aos_mcp_servers` — internal use only

All MCP connectivity is accessed exclusively through `PurposeDrivenAgent` methods.

---

## Standard MCP Servers

| Server | Authority | Domain |
|---|---|---|
| `mind-mvp` | All agents | Cross-session state persistence — reads in `_load_context()`, writes in `_write_state()` |
| `erp-mcp` | CFO agent | ERP events — `erp.burn.exceeded`, `erp.revenue.milestone` |
| `crm-mcp` | CMO agent | CRM events — `crm.lead.qualified`, `crm.churn.signal` |
| `linkedin-mcp` | CMO agent (read) | Market signals — `market.competitor.signal` |

MCP server bindings for domain-specific servers (ERP, CRM, LinkedIn) are configured in the CXO agent layer — not here. This layer provides the client transport primitives only.

---

## `ContextMCPServer`

In-session MCP server for turn-level state sharing. Lightweight — no persistence. Provides context to other tools within a single agent turn.

---

## Context Providers

| Provider | Source | Injection point |
|---|---|---|
| `SubconsciousContextProvider` | Conversation history from `mind-mvp` | `_load_context()` — cross-session memory |
| `SubconsciousSchemaContextProvider` | JSON-LD mind-schema documents from `mind-mvp` | `_load_context()` — structured state |

Both providers inject into `_build_prompt()` before LLM invocation.

---

## Invariants

- `_aos_mcp_servers` never exported from `__init__.py`
- No downstream layer imports `_aos_mcp_servers` directly
- `mind-mvp` is the single persistence layer — all cross-session state flows through it
- MCP reads precede LLM invocation; MCP writes follow routing enforcement

---

## Related Specifications

| Concern | Specification |
|---|---|
| Agent lifecycle | `.github/specs/agent-lifecycle.md` |
| Repository ownership | `.github/specs/repository.md` |
