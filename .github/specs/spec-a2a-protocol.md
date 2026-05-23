# Agent-to-Agent Protocol Specification

**v2.0.0 | A2AAgentTool | AOSProtocol | MCPServerProtocol**

---

## Identity

Structural protocols and tool descriptors for agent-to-agent (A2A) communication within the AOS hierarchy. Implemented in `purpose_driven_agent.agents.protocols` and `purpose_driven_agent.agents.a2a_agent_tool`. Inherited by all CXO agents. Defines the interface contract through which agents invoke peer agents as tools.

Whitepaper: `boardroom-whitepaper-v4.md` §3.1 — The Agent Hierarchy

---

## `AOSProtocol`

PEP 544 structural protocol defining the interface any AOS agent must satisfy. Used for static type checking across the hierarchy — not for runtime isinstance checks.

| Method | Contract |
|---|---|
| `get_routing_tags()` | Returns `frozenset[str]` of valid routing tags |
| `get_default_routing_tag()` | Returns `str` — default tag when none present |
| `enforce_routing_tag(response_text)` | Returns `str` — response with guaranteed valid tag |
| `run_turn(session)` | Returns `TurnResult` — one LLM call, deterministic lifecycle |

---

## `MCPServerProtocol`

PEP 544 structural protocol for MCP servers registered with an agent. Defines the interface `_aos_mcp_servers` implementations must satisfy. Not for public use — internal to `purpose_driven_agent`.

---

## `A2AAgentTool`

Tool descriptor enabling an agent to invoke a peer agent as a tool within a turn. Wraps a Foundry agent reference for use in `_build_prompt()` tool bindings.

| Property | Type | Role |
|---|---|---|
| `name` | `str` | Foundry agent name (e.g. `"cfo-mvp"`) |
| `description` | `str` | Tool description injected into system prompt |
| `agent_reference` | `AgentReference` | Foundry `agent_reference` payload for Responses API |

`A2AAgentTool` instances are declared at the CXO agent class level — not constructed at runtime. The orchestrator (`FounderAgent`) holds `A2AAgentTool` references to specialists (`CFOAgent`, `CMOAgent`). Tool invocation is mediated by the Boardroom workflow, not by direct Python call.

---

## Hierarchy Communication Pattern

```
FounderAgent (orchestrator)
  tools: [A2AAgentTool("cfo-mvp"), A2AAgentTool("cmo-mvp")]
    → [ROUTE:CFO] → Boardroom workflow → InvokeAzureAgent("cfo-mvp")
    → [ROUTE:CMO] → Boardroom workflow → InvokeAzureAgent("cmo-mvp")
    ← [HANDBACK]  ← CFOAgent / CMOAgent response
```

Agents do not call each other directly. Routing tags signal intent; the Boardroom workflow (Layer 1) executes the invocation. `A2AAgentTool` provides the metadata the workflow needs.

---

## Invariants

- `AOSProtocol` and `MCPServerProtocol` are structural (PEP 544) — no runtime isinstance enforcement
- `A2AAgentTool` is declarative — instantiated at class definition, not at runtime
- Agents never invoke peer agents directly — all A2A communication routes through the Boardroom workflow
- `A2AAgentTool.name` must match the Foundry agent name exactly — case-sensitive

---

## Related Specifications

| Concern | Specification |
|---|---|
| Routing protocol | `.github/specs/routing-protocol.md` |
| FAS hosting | `.github/specs/fas-hosting.md` |
| Agent lifecycle | `.github/specs/agent-lifecycle.md` |
| Repository ownership | `.github/specs/repository.md` |
