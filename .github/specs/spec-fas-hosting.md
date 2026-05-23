# FAS Hosting Specification

**v2.0.0 | agent-framework-foundry-hosting 1.0.0a260507**

---

## Identity

Foundry Agent Service (FAS) hosting adapter for the AOS agent hierarchy. Encapsulated entirely in `purpose_driven_agent.hosting`. Every agent in the hierarchy — `LeadershipAgent`, `BusinessAgent`, all CXO agents — runs as a FAS hosted container via this adapter. Zero FAS wiring in downstream layers.

Whitepaper: `boardroom-whitepaper-v4.md` §3.2 — FAS Hosting Architecture

---

## Entry Point

`python -m purpose_driven_agent` — CMD for every agent image in the neutral network.

Execution sequence:
1. `__main__.py` — imports `AGENT_PACKAGE` env var via `importlib.import_module()`, pre-seeding `__init_subclass__` registry with leaf agent class
2. `hosting.run_server()` — discovery pipeline → `AgentServer` wiring → serve

---

## Discovery Pipeline

Priority-ordered. First match wins.

| Priority | Mechanism | Key |
|---|---|---|
| 1 | `importlib.metadata.entry_points(group="agent_framework.hosted_agents")` | `AGENT_ENTRY_POINT` env var (default: `"default"`) |
| 2 | `PurposeDrivenAgent.get_hosted_agent()` | `max(_AGENT_REGISTRY.values(), key=lambda c: len(c.__mro__))` |
| 3 | `PurposeDrivenAgent` | Fallback — logs warning |

---

## `AGENT_PACKAGE` Pre-Seeding

`_ensure_imports()` walks `/app` alphabetically, importing every top-level package. Without pre-seeding, an intermediate layer class (e.g. `BusinessAgent`) registers before the leaf class (e.g. `FounderAgent`) — discovery returns the wrong class.

`AGENT_PACKAGE` env var (e.g. `founder_agent`) is imported in `__main__.py` before `run_server()` fires, guaranteeing the leaf class is registered first.

---

## `AgentServer` Contract

Import path resolved at runtime from installed `agent-framework-foundry-hosting` — not hardcoded. `pkgutil.walk_packages` or `importlib.metadata` used to discover actual module path. All attempted paths logged at `ERROR` before `sys.exit(1)` on failure.

Wiring:
```
AgentServer().register(agent_class())
AgentServer().serve(port=AGENT_SERVICE_PORT)
```

---

## Runtime Environment

| Variable | Role |
|---|---|
| `PYTHONPATH` | `/app:/app/lib/python3.12/site-packages` — baked into image via `Dockerfile.aos-agent` |
| `AGENT_PACKAGE` | Leaf agent package name — pre-seeds registry |
| `AGENT_ENTRY_POINT` | Entry point key for `importlib.metadata` discovery (default: `"default"`) |
| `AGENT_SERVICE_PORT` | HTTP port for `AgentServer.serve()` (default: `8000`) |
| `LOG_LEVEL` | Logging verbosity (default: `INFO`) |

---

## Invariants

- `run_server()` defined once — in `purpose_driven_agent.hosting` only
- `__main__.py` defined once — in `purpose-agent` only; no downstream repo defines its own
- `AgentServer` import path never hardcoded — always runtime-resolved
- Discovery never returns an abstract class in production
- `AGENT_PACKAGE` pre-seeding precedes `_ensure_imports()` alphabetical walk

---

## Related Specifications

| Concern | Specification |
|---|---|
| Agent registry | `.github/specs/agent-registry.md` |
| Routing protocol | `.github/specs/routing-protocol.md` |
| Repository ownership | `.github/specs/repository.md` |
