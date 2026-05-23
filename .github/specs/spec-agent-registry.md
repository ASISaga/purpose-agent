# Agent Registry Specification

**v2.0.0 | PurposeDrivenAgent.__init_subclass__**

---

## Identity

`__init_subclass__`-based auto-registration mechanism for `PurposeDrivenAgent` subclasses. Implemented in `purpose_driven_agent.agents.purpose_driven_agent`. Enables runtime discovery of the most-derived concrete agent class without explicit registration calls.

Whitepaper: `boardroom-whitepaper-v4.md` §3.2 — FAS Hosting Architecture

---

## Registration Contract

Every class that inherits from `PurposeDrivenAgent` — directly or transitively — is registered automatically at class definition time via `__init_subclass__`. No explicit registration call required.

| Property | Value |
|---|---|
| Registry type | `dict[str, type[PurposeDrivenAgent]]` |
| Registry key | `cls.__qualname__` |
| Registration trigger | Class definition (`__init_subclass__`) |
| Registration precondition | Module containing class has been imported |

---

## `get_hosted_agent()` Contract

Returns the most-derived registered concrete subclass by MRO length.

| Condition | Returns |
|---|---|
| Registry non-empty, concrete classes present | `max(_AGENT_REGISTRY.values(), key=lambda c: len(c.__mro__))` |
| Registry empty | `PurposeDrivenAgent` (fallback) |

Invariant: never returns an abstract class in production. `GenericPurposeDrivenAgent` exists as the concrete fallback for test environments.

---

## Import Ordering Problem

`_ensure_imports()` in `hosting.py` walks `/app` alphabetically. In a multi-layer image:

```
/app/business_agent/     ← imported before founder_agent
/app/founder_agent/      ← imported after business_agent
/app/leadership_agent/   ← imported before founder_agent
/app/purpose_driven_agent/
```

`BusinessAgent` registers before `FounderAgent` — both are concrete. `get_hosted_agent()` returns the class with the longer MRO, but only if both are imported. Without `AGENT_PACKAGE` pre-seeding, alphabetical import ordering can cause `BusinessAgent` (shorter name) to be the only registered concrete subclass if `founder_agent` hasn't been imported yet.

---

## `AGENT_PACKAGE` Resolution

`__main__.py` imports `AGENT_PACKAGE` env var before calling `run_server()`. This guarantees the leaf agent class registers before `_ensure_imports()` fires, regardless of alphabetical ordering.

| Step | Effect |
|---|---|
| `importlib.import_module("founder_agent")` | `FounderAgent.__init_subclass__` → registered |
| `_ensure_imports()` walks `/app` | All other classes registered |
| `get_hosted_agent()` | Returns `FounderAgent` (longest MRO) |

---

## Invariants

- Every `PurposeDrivenAgent` subclass auto-registers at import time — no explicit call
- `get_hosted_agent()` is deterministic and side-effect-free
- Abstract classes must not win discovery — `GenericPurposeDrivenAgent` exists to prevent `PurposeDrivenAgent` fallback in test
- `AGENT_PACKAGE` pre-seeding is mandatory for correct leaf class discovery in multi-layer images

---

## Related Specifications

| Concern | Specification |
|---|---|
| FAS hosting adapter | `.github/specs/fas-hosting.md` |
| Routing protocol | `.github/specs/routing-protocol.md` |
| Repository ownership | `.github/specs/repository.md` |
