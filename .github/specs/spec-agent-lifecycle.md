# Agent Lifecycle Specification

**v2.0.0 | PurposeDrivenAgent — Perpetual Operation**

---

## Identity

Deterministic per-turn execution lifecycle for `PurposeDrivenAgent`. Python owns the program — the LLM is called exactly once per turn as an English API for natural language reasoning. All other operations are deterministic, auditable Python.

Whitepaper: `boardroom-whitepaper-v4.md` §2.4 — The LLM as English API

---

## Turn Lifecycle

Fixed sequence. Not configurable by subclasses. One LLM call per turn.

| Step | Owner | Operation |
|---|---|---|
| 1 | Python | `_load_context(session)` — Mind MCP reads, JSON-LD state injection |
| 2 | Python | `_build_prompt(context, session)` — structured prompt assembly |
| 3 | LLM | `_invoke_llm(prompt)` — one English API call |
| 4 | Python | `_parse_response(raw)` — deterministic parsing |
| 5 | Python | `_validate(response)` — Pydantic schema validation |
| 6 | Python | `enforce_routing_tag(validated)` — routing protocol guarantee |
| 7 | Python | `_write_state(routing, session)` — Mind MCP writes, audit trail |
| 8 | Python | Return `TurnResult(content, route)` |

Invariant: steps 1, 2, 4, 5, 6, 7, 8 have full stack traces. Step 3 is the only non-deterministic boundary.

---

## Perpetual Operation

Agents run indefinitely toward their assigned purpose. A turn does not terminate the agent. Session termination occurs only via routing tag:

| Tag | Termination |
|---|---|
| `[COMPLETE]` | Orchestrator session terminates — deliberation converged |
| `[HANDBACK]` | Specialist turn terminates — control returned to orchestrator |

No other termination condition. Agents persist across sessions via Mind MCP state.

---

## Context Injection

`_load_context()` assembles the inference context from two sources:

| Source | Provider | Content |
|---|---|---|
| Conversation history | `SubconsciousContextProvider` | Cross-session memory from Mind MCP server |
| JSON-LD mind-schema | `SubconsciousSchemaContextProvider` | Structured state documents — company state, agenda, decision log |

Context is injected into `_build_prompt()` before LLM invocation.

---

## Audit Trail

Every non-LLM step produces an auditable record:
- State reads: Mind MCP read provenance
- State writes: Mind MCP write provenance with decision rationale
- Routing decisions: tag, source (valid/invalid/absent), applied default
- Validation failures: Pydantic errors → `ResponseValidationError` — hard failure, no retry

---

## ML Interface

`IMLService` is the boundary through which AOS drives per-avatar LoRA adaptation. `PurposeDrivenAgent` holds a reference to an `IMLService` instance. AOS owns the fine-tuning pipeline — this interface is the contract boundary. `NoOpMLService` raises `NotImplementedError` on use — default until AOS wires a real adapter.

---

## Invariants

- Exactly one `_invoke_llm()` call per turn — never zero, never more than one
- `enforce_routing_tag()` always follows `_validate()` — never bypassed
- `ResponseValidationError` on Pydantic failure — no silent fallback
- Mind MCP write always follows successful routing enforcement — no orphaned state
- Perpetual operation — no agent self-terminates; only routing tags terminate turns/sessions

---

## Related Specifications

| Concern | Specification |
|---|---|
| Routing protocol | `.github/specs/routing-protocol.md` |
| FAS hosting | `.github/specs/fas-hosting.md` |
| Agent registry | `.github/specs/agent-registry.md` |
| Repository ownership | `.github/specs/repository.md` |
