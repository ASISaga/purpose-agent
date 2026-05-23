# LLM as English API Specification

**v2.0.0 | PurposeDrivenAgent._invoke_llm()**

---

## Identity

The LLM is an API — called exactly once per agent turn for natural language reasoning, domain judgment, and voice. Python owns the program. Every step before and after `_invoke_llm()` is deterministic, auditable Python. This boundary is the architectural foundation of AOS agent auditability.

Whitepaper: `boardroom-whitepaper-v4.md` §2.4 — The LLM as English API

---

## The Boundary

```
Python                    LLM                      Python
──────────────────────    ─────────────────────    ──────────────────────────
_load_context()       →                            
_build_prompt()       →                            
                          _invoke_llm(prompt)      
                      ←   raw response             
                                                   _parse_response(raw)
                                                   _validate(response)
                                                   enforce_routing_tag()
                                                   _write_state()
```

The LLM boundary is a single call with a single return. No streaming decision logic. No multi-step LLM chains. No LLM-orchestrated tool calls. One English API call per turn.

---

## Prompt Assembly Contract

`_build_prompt()` assembles the prompt from structured inputs — deterministic, reproducible, auditable.

| Component | Source | Role |
|---|---|---|
| System prompt | Agent class definition | Persona, purpose, routing instructions |
| JSON-LD context | `SubconsciousSchemaContextProvider` | Current reality — company state, agenda, decisions |
| Conversation history | `SubconsciousContextProvider` | Cross-session memory |
| Turn input | `session.current_input` | Current deliberation prompt |

Prompt structure is owned by the agent class. `PurposeDrivenAgent` defines the assembly contract; subclasses inject persona-specific content.

---

## Response Parsing Contract

`_parse_response(raw)` is deterministic — no LLM call, no retry, no fallback generation.

| Condition | Action |
|---|---|
| Parseable response | Returns structured `AgentResponse` |
| Unparseable response | Raises `ResponseParseError` — hard failure |

`_validate(response)` applies Pydantic schema validation after parsing.

| Condition | Action |
|---|---|
| Valid response | Returns validated response |
| Invalid response | Raises `ResponseValidationError` — hard failure, no silent fallback |

---

## LLM Provider Contract

`_invoke_llm()` calls the MAF `agent-framework` LLM interface. Provider configuration (model, temperature, context window) is owned by the MAF framework and AOS — not by `PurposeDrivenAgent`. The agent is provider-agnostic at the code level.

LoRA adapter injection (avatar persona) is handled by `IMLService` — the adapter is applied at the MAF layer before the LLM call reaches the base model. `PurposeDrivenAgent` holds a reference to an `IMLService` instance; AOS wires the concrete adapter.

---

## Avatar Voice

The LLM call is where the avatar persona manifests — Paul Graham's directness, Buffett's financial discipline, Godin's marketing sensibility. This is the only point in the turn lifecycle where non-deterministic, persona-specific language is generated.

The system prompt carries the persona framing. The LoRA adapter (when active) shifts the base model toward the avatar's voice at the weight level. Context engineering (JSON-LD state injection) grounds the avatar in current reality rather than hallucinated context.

---

## Invariants

- Exactly one `_invoke_llm()` call per turn — never zero, never more than one
- `_invoke_llm()` is never called from outside `run_turn()` — no ad-hoc LLM calls
- No LLM call in `_parse_response()`, `_validate()`, or `enforce_routing_tag()`
- `ResponseValidationError` on Pydantic failure — no retry, no silent fallback
- Prompt assembly is fully deterministic and reproducible from inputs alone
- LLM provider and model are configured at the MAF/AOS layer — not hardcoded in agent code

---

## Related Specifications

| Concern | Specification |
|---|---|
| Agent lifecycle | `.github/specs/agent-lifecycle.md` |
| Subconscious | `.github/specs/subconscious.md` |
| Routing protocol | `.github/specs/routing-protocol.md` |
| Repository ownership | `.github/specs/repository.md` |
