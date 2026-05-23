# Subconscious Specification

**v2.0.0 | Mind MCP — Cross-Session Persistence and Context Injection**

---

## Identity

The subconscious is the cross-session memory and identity layer for AOS agents. Implemented via the `mind-mvp` MCP server. Provides persistent state that survives session boundaries — conversation history, structured JSON-LD mind-schema documents, decision provenance. Injected into every agent turn via `SubconsciousContextProvider` and `SubconsciousSchemaContextProvider` before LLM invocation.

Whitepaper: `boardroom-whitepaper-v4.md` §8 — Context Engineering, §4.2 — Standard MCP Servers

---

## Architecture

```
mind-mvp MCP server                          External process
  ├── Conversation history store             Per-agent, cross-session
  └── JSON-LD mind-schema document store     Typed, provenance-tracked
        ├── asi-saga-state.jsonld
        ├── asi-saga-vision.jsonld
        ├── boardroom-state.jsonld
        ├── boardroom-vision.jsonld
        ├── agenda.jsonld
        ├── decision-log.jsonld
        └── agent-definitions.jsonld

PurposeDrivenAgent._load_context(session)
  ├── SubconsciousContextProvider            → conversation history read
  └── SubconsciousSchemaContextProvider      → JSON-LD document read
        → context injected into _build_prompt()
```

---

## Context Providers

### `SubconsciousContextProvider`

Reads conversation history from `mind-mvp`. Provides the agent's cross-session memory — prior deliberations, decisions made, positions taken. Authority: all agents.

| Property | Value |
|---|---|
| Source | `mind-mvp` conversation history store |
| Read point | `_load_context()` — before every LLM invocation |
| Injection point | `_build_prompt()` — conversation memory context block |
| Factory | `create_subconscious_provider()` |
| Config | `SUBCONSCIOUS_MCP_URL` env var |

### `SubconsciousSchemaContextProvider`

Reads JSON-LD mind-schema documents from `mind-mvp`. Provides typed, structured state — company financials, market position, agenda, decision log. Grounds avatar reasoning in current reality rather than hallucinated context.

| Property | Value |
|---|---|
| Source | `mind-mvp` JSON-LD document store |
| Read point | `_load_context()` — before every LLM invocation |
| Injection point | `_build_prompt()` — structured state context block |
| Factory | `create_subconscious_schema_provider()` |
| Document authority | Per JSON-LD file (see State Authority below) |

---

## State Authority

Each JSON-LD document has a defined authority — the agent or system that writes it.

| Document | Authority | Content |
|---|---|---|
| `asi-saga-state.jsonld` | AOS | Company state — financial, market, operational |
| `asi-saga-vision.jsonld` | AOS | North star, evolution phases |
| `boardroom-state.jsonld` | AOS | Product capabilities, agent status, workflow state |
| `boardroom-vision.jsonld` | AOS | Architecture layers, capability roadmap |
| `agenda.jsonld` | `FounderAgent` | Current agenda, queued items, open questions |
| `decision-log.jsonld` | All agents | Append-only decision log with counterfactuals |
| `agent-definitions.jsonld` | AOS | Avatar personas, LoRA configs, injection rules |

Write authority is enforced by `BoardroomGenerator` in the AOS layer — agents write only to documents within their state authority.

---

## Write Contract

State writes occur in `_write_state()` — after `enforce_routing_tag()`, before `TurnResult` is returned.

| Property | Value |
|---|---|
| Write point | `_write_state(routing, session)` |
| Provenance | Every write tagged with agent identity, session ID, turn number, timestamp |
| Decision log | Append-only — counterfactuals recorded alongside decisions taken |
| Validation | `BoardroomValidator` enforces schema, semantic, and cross-file consistency |

---

## `ContextMCPServer`

In-session MCP server distinct from `mind-mvp`. Lightweight, in-process. Provides turn-level context sharing within a single agent session. Not persistent — state is lost at session end. Complements `mind-mvp` for intra-turn coordination.

---

## Invariants

- `mind-mvp` is the single persistence layer — no agent writes state outside of it
- `SubconsciousContextProvider` reads precede every LLM invocation without exception
- Decision log is append-only — no mutation of prior decisions
- Write authority enforced at the AOS layer — not at the agent layer
- `SUBCONSCIOUS_MCP_URL` env var configures the Mind MCP endpoint — not hardcoded

---

## Related Specifications

| Concern | Specification |
|---|---|
| MCP connectivity | `.github/specs/mcp-connectivity.md` |
| Agent lifecycle | `.github/specs/agent-lifecycle.md` |
| Repository ownership | `.github/specs/repository.md` |
