# purpose-driven-agent Repository Specification

**v2.0.0 | Python 3.12 | MAF 1.3.0 | FAS 1.0.0a260507**

---

## Identity

Layer 2 of the AOS ACR neutral network. Implements `PurposeDrivenAgent` — the abstract base class from which all AOS CXO agents inherit perpetual operation, FAS hosting, routing protocol enforcement, and MCP connectivity. Single source of truth for the agent lifecycle, FAS entry point, and routing contract. Zero re-implementation in downstream layers.

Whitepaper: `boardroom-whitepaper-v4.md` §3 — Layer 2: MAF CXO Agents

---

## Neutral Network Position

```
aos/infra                                   Layer 0 — external dependencies (.pyc)
  └── aos/purpose-driven-agent              Layer 2 — THIS REPO
        └── aos/leadership-agent            Layer 3
              └── aos/business-agent        Layer 4
                    └── aos/{cxo}-agent     Layer 5 — leaf agents
```

| Property | Value |
|---|---|
| ACR image | `acraosstagingerm2srfd.azurecr.io/aos/purpose-driven-agent` |
| Parent | `aos/infra` |
| Build artefact | `.pyc` only — `compileall -b -j0`, `.py` absent from image |
| CMD | `python -m purpose_driven_agent` |
| Downstream propagation | `manifest-update` dispatch → `ASISaga/leadership-agent` on push to `main` |
| Non-breaking parent bump | `crane rebase` — zero recompilation, manifest pointer update only |

---

## Module Ownership

| Module | Public Surface | Contract |
|---|---|---|
| `agents.purpose_driven_agent` | `PurposeDrivenAgent` ABC | `__init_subclass__` registry; `get_hosted_agent()` → most-derived subclass by MRO length; `enforce_routing_tag()` on every LLM response; one `_invoke_llm()` call per turn |
| `agents.generic_purpose_driven_agent` | `GenericPurposeDrivenAgent` | Concrete non-abstract subclass; instantiable for testing |
| `agents.protocols` | `MCPServerProtocol`, `AOSProtocol` | PEP 544 structural protocols |
| `agents.a2a_agent_tool` | `A2AAgentTool` | Agent-to-agent tool descriptor |
| `routing_mixin` | `RoutingMixin` | `ROUTING_ROLE` ∈ {`orchestrator`, `specialist`}; derives valid tag set and default tag; mixed into every CXO class |
| `hosting` | `run_server()` | Single FAS entry point for entire agent hierarchy; discovery pipeline: `importlib.metadata` entry point → `get_hosted_agent()` registry → `PurposeDrivenAgent` fallback |
| `__main__` | — | `AGENT_PACKAGE` env var → `importlib.import_module()` pre-seeds registry → `run_server()`; defined once, here only |
| `context_server` | `ContextMCPServer` | In-session MCP state server |
| `context_providers` | `ContextProvider`, `SubconsciousContextProvider`, `SubconsciousSchemaContextProvider`, factories | Conversation history and JSON-LD mind-schema injection at inference time |
| `ml_interface` | `IMLService`, `NoOpMLService` | LoRA adapter boundary; AOS owns fine-tuning pipeline |
| `_aos_mcp_servers` | — | Internal MCP client primitives; not in `__all__`; not importable by downstream layers |

---

## Architectural Contracts

**Agent Registry** — `__init_subclass__` auto-registers every `PurposeDrivenAgent` subclass at class definition time. `get_hosted_agent()` is deterministic: returns `max(_AGENT_REGISTRY.values(), key=lambda c: len(c.__mro__))`. Never returns an abstract class in production.

**Routing Enforcement** — `enforce_routing_tag()` is a post-LLM code guarantee on every agent turn. Scans response tail (last 200 chars), enforces membership in `get_routing_tags()`, appends `get_default_routing_tag()` if absent. Routing is a code contract — not a prompt instruction.

**LLM Boundary** — exactly one `_invoke_llm()` per turn. All other operations are deterministic Python: context load, prompt assembly, Pydantic validation, routing enforcement, Mind MCP writes. Audit trail spans all non-LLM steps.

**FAS Entry Point** — `python -m purpose_driven_agent` is the runtime CMD for every agent in the hierarchy. `__main__.py` is defined once in this repo. `AGENT_PACKAGE` env var pre-seeds the registry with the leaf agent class before `_ensure_imports()` alphabetical walk; prevents intermediate layer class (e.g. `BusinessAgent`) from winning discovery over the leaf class (e.g. `FounderAgent`).

**MCP Encapsulation** — `_aos_mcp_servers` is a private implementation detail. Downstream agents access MCP connectivity exclusively through `PurposeDrivenAgent` methods. Never exposed in `__all__`, never imported directly by downstream.

**Perpetual Operation** — agents run indefinitely. Turn termination occurs only via `[COMPLETE]` (orchestrators) or `[HANDBACK]` (specialists) routing tags.

---

## Routing Protocol

Defined here. Enforced in code. Propagated by inheritance to all downstream agents.

| Tag | Role | Semantics |
|---|---|---|
| `[ROUTE:CFO]` | `orchestrator` | Delegate turn to CFO specialist |
| `[ROUTE:CMO]` | `orchestrator` | Delegate turn to CMO specialist |
| `[COMPLETE]` | `orchestrator` | Deliberation converged — terminate session |
| `[HANDBACK]` | `specialist` | Return control to orchestrator |

Extensible: new `[ROUTE:*]` tags declared in `routing_mixin` as CXO specialists are added to the hierarchy.

---

## Technology Stack

| Package | Version | Role |
|---|---|---|
| `agent-framework` | 1.3.0 | Microsoft Agent Framework (MAF) base |
| `agent-framework-foundry` | 1.3.0 | FAS client |
| `agent-framework-foundry-hosting` | 1.0.0a260507 | FAS server — `AgentServer` |
| `azure-identity` | 1.21.0 | Keyless OIDC / Entra authentication |
| `pydantic` | 2.11.4 | Response schema validation |
| `azure-servicebus` | 7.14.2 | Event-driven triggering |
| `opentelemetry-sdk` | 1.40.0 | Observability |

All runtime dependencies compiled to `.pyc` in `aos/infra`. This repo compiles only its own source.

---

## Invariants

- `enforce_routing_tag()` called on every LLM response — always code, never prompt
- `get_hosted_agent()` never returns an abstract class in production
- `__main__.py` defined once — in this repo only; no downstream repo defines its own FAS entry point
- `_aos_mcp_servers` never in `__all__`, never imported directly by downstream
- `Dockerfile.aos-agent` is owned by `ASISaga/aos-infra` — not modified in this repo
- `RoutingMixin` is the only routing contract — downstream agents mix it in, do not re-implement

---

## Specifications

| Specification | Concern |
|---|---|
| `.github/specs/fas-hosting.md` | FAS hosting adapter — entry point, discovery pipeline, `AgentServer` wiring |
| `.github/specs/routing-protocol.md` | Routing tags, `RoutingMixin`, `enforce_routing_tag()`, dual-guard pattern |
| `.github/specs/agent-registry.md` | `__init_subclass__` registry, `get_hosted_agent()`, `AGENT_PACKAGE` pre-seeding |
| `.github/specs/agent-lifecycle.md` | Per-turn execution sequence, perpetual operation, audit trail, ML interface |
| `.github/specs/llm-api.md` | LLM boundary — one call per turn, prompt assembly, response parsing, avatar voice, LoRA injection |
| `.github/specs/mcp-connectivity.md` | `_aos_mcp_servers` encapsulation, standard MCP servers, context providers |
| `.github/specs/subconscious.md` | Mind MCP persistence, `SubconsciousContextProvider`, JSON-LD state authority, write provenance |
| `.github/specs/neutral-network-build.md` | `.pyc` compilation, ACR Task build, propagation, link verification |
| `.github/specs/a2a-protocol.md` | `A2AAgentTool`, `AOSProtocol`, `MCPServerProtocol` — agent-to-agent communication |
| `.github/specs/ml-interface.md` | `IMLService`, `NoOpMLService` — LoRA adapter boundary, dataset pipeline, TIES merge |
| `.github/specs/public-api.md` | `__all__`, versioning policy, backward compatibility, downstream import contract |
| `.github/specs/agent-intelligence-framework.md` | MAF agent framework contracts |

## Related Repositories

| Repository | Relationship |
|---|---|
| `ASISaga/aos-infra` | Parent layer; owns `Dockerfile.aos-agent` and `aos-agent-build.yml` |
| `ASISaga/leadership-agent` | Immediate downstream; receives `manifest-update` on push to `main` |
| `ASISaga/business-agent` | Layer 4 downstream |
| `ASISaga/{cxo}-agent` | Layer 5 leaf agents — all inherit from this layer |
