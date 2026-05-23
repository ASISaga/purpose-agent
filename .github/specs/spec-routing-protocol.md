# Routing Protocol Specification

**v2.0.0 | Boardroom Deliberation Layer**

---

## Identity

Code-enforced routing protocol for the AOS Boardroom deliberation engine. Defined in `purpose_driven_agent.routing_mixin`. Enforced in `PurposeDrivenAgent.enforce_routing_tag()`. Inherited by every CXO agent. The LLM system prompt instructs — `enforce_routing_tag()` guarantees.

Whitepaper: `boardroom-whitepaper-v4.md` §2.2 — Deliberation Engine, §3.3 — Routing Enforcement in Code

---

## Routing Tags

| Tag | `ROUTING_ROLE` | Semantics | Default |
|---|---|---|---|
| `[ROUTE:CFO]` | `orchestrator` | Delegate turn to CFO specialist | — |
| `[ROUTE:CMO]` | `orchestrator` | Delegate turn to CMO specialist | — |
| `[COMPLETE]` | `orchestrator` | Deliberation converged — terminate session | ✓ |
| `[HANDBACK]` | `specialist` | Return control to orchestrator | ✓ |

Extensible: new `[ROUTE:*]` tags declared in `RoutingMixin` as CXO specialists are added to the hierarchy.

---

## `RoutingMixin`

Declares routing role. Mixed into every concrete CXO agent class.

| `ROUTING_ROLE` | `get_routing_tags()` | `get_default_routing_tag()` |
|---|---|---|
| `"orchestrator"` | `frozenset({[ROUTE:CFO], [ROUTE:CMO], [COMPLETE]})` | `[COMPLETE]` |
| `"specialist"` | `frozenset({[HANDBACK]})` | `[HANDBACK]` |

Usage: `class FounderAgent(RoutingMixin, BusinessAgent): ROUTING_ROLE = "orchestrator"`

---

## `enforce_routing_tag()` Contract

Called on every LLM response, before result is returned to the Boardroom workflow. Operates on response tail (last 200 chars).

| Condition | Action |
|---|---|
| Valid tag found | Return response unchanged |
| Invalid tag found | Replace with `get_default_routing_tag()` |
| No tag found | Append `get_default_routing_tag()` on new line |

Invariant: every response returned by an AOS agent contains exactly one valid routing tag.

---

## Dual-Guard Pattern (Boardroom Workflow)

The `boardroom-mvp` workflow enforces routing at the orchestration layer as a secondary guard:

| Guard | Mechanism |
|---|---|
| Primary | `Local.RouteTo` — structured output binding |
| Fallback | `Find("[ROUTE:CFO]", Upper(Local.LatestMessage))` — text scan |

`enforce_routing_tag()` in the agent is the first guard. The dual-guard in the workflow is defence-in-depth.

---

## Invariants

- `enforce_routing_tag()` called on every LLM response without exception
- Routing is a code contract — never delegated to prompt instruction alone
- `RoutingMixin` is the single definition of valid tag sets — no downstream redefinition
- Orchestrators never emit `[HANDBACK]`; specialists never emit `[ROUTE:*]` or `[COMPLETE]`
- `get_hosted_agent()` discovery and routing role are independent concerns — `RoutingMixin` is not involved in discovery

---

## Related Specifications

| Concern | Specification |
|---|---|
| FAS hosting adapter | `.github/specs/fas-hosting.md` |
| Agent registry | `.github/specs/agent-registry.md` |
| Repository ownership | `.github/specs/repository.md` |
