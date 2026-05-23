# Public API Specification

**v2.0.0 | purpose_driven_agent.__all__ | Versioning | Backward Compatibility**

---

## Identity

The public interface contract of the `purpose_driven_agent` package as consumed by downstream layers (`leadership-agent`, `business-agent`, CXO agents). Defines `__all__`, versioning policy, and backward compatibility guarantees. All downstream layers import exclusively from `purpose_driven_agent` — never from internal submodules.

---

## `__all__`

The complete public surface of this package. Downstream layers import only from this set.

```python
__all__ = [
    # Agent classes
    "PurposeDrivenAgent",
    "GenericPurposeDrivenAgent",
    "A2AAgentTool",

    # Protocols
    "MCPServerProtocol",
    "AOSProtocol",

    # MCP state
    "ContextMCPServer",

    # Context providers
    "Context",
    "ContextProvider",
    "SubconsciousContextProvider",
    "SubconsciousSchemaContextProvider",
    "create_subconscious_provider",
    "create_subconscious_schema_provider",
    "SUBCONSCIOUS_MCP_URL",

    # ML interface
    "IMLService",
    "NoOpMLService",
]
```

**Explicitly excluded from `__all__`:**

| Symbol | Reason |
|---|---|
| `RoutingMixin` | Mixed in by downstream — importable but not in `__all__` |
| `_aos_mcp_servers` | Private subpackage — never importable by downstream |
| `run_server` | FAS infrastructure — not part of agent authoring API |
| `_AGENT_REGISTRY` | Internal registry — not for external access |

---

## Versioning

`__version__ = "2.0.0"` in `__init__.py`. Semantic versioning:

| Change type | Version bump | Cascade required |
|---|---|---|
| Breaking change to `__all__` surface | Major | All downstream layers must update |
| New symbol added to `__all__` | Minor | Optional update downstream |
| Internal refactor, no API change | Patch | `crane rebase` only — zero recompilation |

---

## Backward Compatibility Contract

- Symbols in `__all__` are stable across patch and minor versions
- Method signatures of `PurposeDrivenAgent` abstract methods (`get_routing_tags`, `get_default_routing_tag`, `enforce_routing_tag`, `run_turn`) are stable across minor versions
- `ROUTING_ROLE` values (`"orchestrator"`, `"specialist"`) are stable — extending requires a minor version bump
- `_aos_mcp_servers` is never part of the public API — downstream code depending on it is invalid

---

## Import Contract for Downstream Layers

All downstream layers (`LeadershipAgent`, `BusinessAgent`, CXO agents) import exclusively at the package level:

```python
# Correct
from purpose_driven_agent import PurposeDrivenAgent, RoutingMixin

# Incorrect — never import from internal submodules
from purpose_driven_agent.agents.purpose_driven_agent import PurposeDrivenAgent
from purpose_driven_agent._aos_mcp_servers import ...
```

Submodule import paths are not stable — only `__all__` members are stable.

---

## Invariants

- `__all__` is the complete and authoritative public surface — no undocumented exports
- `_aos_mcp_servers` never appears in `__all__` under any version
- `RoutingMixin` is importable but not in `__all__` — this is intentional and stable
- Downstream layers never import from internal submodules — only from package root
- Breaking changes to `__all__` require a major version bump and full cascade rebuild

---

## Related Specifications

| Concern | Specification |
|---|---|
| Agent registry | `.github/specs/agent-registry.md` |
| Neutral network build | `.github/specs/neutral-network-build.md` |
| Repository ownership | `.github/specs/repository.md` |
