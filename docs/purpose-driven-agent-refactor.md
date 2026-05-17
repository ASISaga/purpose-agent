# Purpose-Driven Agent — FAS Hosting Refactor Requirements

**Repository:** `ASISaga/purpose-driven-agent`  
**Target audience:** Claude Sonnet 4.6 inside GitHub Copilot coding agent  
**Purpose:** Add the generic FAS hosting infrastructure that every AOS agent layer inherits. No agent-specific logic lives here — only the plumbing that makes any descendant hostable by Azure AI Foundry Agent Service.

---

## Context and Architecture

The AOS container hierarchy is:

```
infrastructure          (Layer 1) — Python 3.12, MAF 1.3.0, agent-framework-foundry-hosting
  └── purpose-driven-agent (Layer 2) — THIS REPO — PurposeDrivenAgent + aos_mcp_servers
        └── leadership-agent   (Layer 3)
              └── business-agent    (Layer 4)
                    └── founder-agent     (Layer 5, FAS target)
```

`agent-framework-foundry-hosting==1.0.0a260507` is already installed in the infrastructure layer. Its job is to start an HTTP server that implements the FAS wire protocol, receive invocations from Foundry, and dispatch them to a registered agent class. **This repo must provide the registration mechanism and the base class contract that all agents implement.**

### Key constraints derived from prior work

- Package layout: `src/purpose_driven_agent/` and `src/aos_mcp_servers/` — both are built packages
- Python 3.12 strictly (`.pyc` bytecode is not cross-version)
- Compilation uses `python -m compileall -b -j0 -q` — the `-b` flag writes `.pyc` beside `.py`, not in `__pycache__/`, so `SourcelessFileLoader` finds them when `.py` files are deleted in the FAS stage
- Runtime user is `aosuser` (non-root, created in infrastructure layer)
- `PYTHONPATH=/app` is set in the container environment
- `aos_mcp_servers.routing` is imported by `purpose_driven_agent.agent` — both packages must be present and on path

---

## Decision 1: FAS Entry Point Discovery

**Decision made:** Use a `pyproject.toml` entry point group `agent_framework.hosted_agents`.

`agent-framework-foundry-hosting` discovers the agent class to host via Python's standard `importlib.metadata` entry points mechanism. The hosting adapter reads the group `agent_framework.hosted_agents` and looks for an entry named `default` (or the value of the env var `AGENT_ENTRY_POINT`, defaulting to `default`).

This means:
- No `AGENT_CLASS` env var string parsing with `importlib.import_module`
- No convention-based `__main__` discovery
- The entry point is declared in `pyproject.toml` — compile-time declaration, not runtime configuration
- Each leaf agent repo declares its own `[project.entry-points."agent_framework.hosted_agents"]` pointing to its class
- `purpose-driven-agent` declares `PurposeDrivenAgent` as the default — overridden by leaf repos

**Why this design:** `importlib.metadata.entry_points()` works on installed packages and also on packages installed in development mode (`pip install -e`). Since the FAS image runs from `/app` with `PYTHONPATH=/app` rather than as an installed package, we need a fallback: the `PurposeDrivenAgent.__init_subclass__` registry pattern (see Decision 2) catches the case where metadata entry points aren't available.

---

## Decision 2: Agent Class Registry (Fallback Discovery)

**Decision made:** `PurposeDrivenAgent` uses `__init_subclass__` to maintain a registry of all subclasses. When the hosting adapter cannot find an entry point via metadata, it calls `PurposeDrivenAgent.get_hosted_agent()` which returns the most-derived registered subclass — i.e., `FounderAgent` if that's what's in the image.

```python
# In purpose_driven_agent/agent.py

_AGENT_REGISTRY: dict[str, type["PurposeDrivenAgent"]] = {}

class PurposeDrivenAgent:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        _AGENT_REGISTRY[cls.__qualname__] = cls

    @classmethod
    def get_hosted_agent(cls) -> type["PurposeDrivenAgent"]:
        """Return the most-derived registered subclass, or cls itself."""
        if not _AGENT_REGISTRY:
            return cls
        # Most-derived: the one whose MRO is longest
        return max(_AGENT_REGISTRY.values(), key=lambda c: len(c.__mro__))
```

The hosting adapter in `purpose_driven_agent/hosting.py` uses this in priority order:
1. `importlib.metadata` entry point `agent_framework.hosted_agents:default`
2. `PurposeDrivenAgent.get_hosted_agent()` registry fallback
3. `PurposeDrivenAgent` itself if neither yields a subclass

---

## Decision 3: Routing Protocol — In Code, Not LLM Instructions

**Decision made:** Post-processing hook on every agent response. The LLM output is inspected by `RoutingClassifier` in `aos_mcp_servers/routing.py`, which appends the correct routing tag if absent, or validates the one present.

**Why post-processing, not prompt injection:** System prompt routing instructions are LLM-compliance-dependent. The workflow's `routing_check` ConditionGroup reads `Local.LatestMessage` text for `[ROUTE:CFO]`, `[ROUTE:CMO]`, `[COMPLETE]`, or `[HANDBACK]`. If the LLM omits the tag, the workflow silently falls through. Code-level enforcement is unconditional.

**Routing tag protocol (established and proven working):**

| Tag | Emitter | Meaning |
|---|---|---|
| `[ROUTE:CFO]` | Orchestrator agents (e.g., FounderAgent) | Route to CFO specialist |
| `[ROUTE:CMO]` | Orchestrator agents | Route to CMO specialist |
| `[COMPLETE]` | Orchestrator agents | End deliberation |
| `[HANDBACK]` | Specialist agents (CFO, CMO, etc.) | Hand control back to orchestrator |

---

## Required Changes to `src/purpose_driven_agent/`

### 1. `src/purpose_driven_agent/agent.py` — Base class additions

Add the following to the existing `PurposeDrivenAgent` class. Do **not** replace the class — extend it.

```python
# Add at module level, before the class definition
import re
import logging
from typing import ClassVar

_AGENT_REGISTRY: dict[str, "type[PurposeDrivenAgent]"] = {}
logger = logging.getLogger(__name__)

# Inside PurposeDrivenAgent class:

    # ── Registry ──────────────────────────────────────────────────────────
    _routing_tags: ClassVar[frozenset[str]] = frozenset(
        {"[ROUTE:CFO]", "[ROUTE:CMO]", "[COMPLETE]", "[HANDBACK]"}
    )

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        _AGENT_REGISTRY[cls.__qualname__] = cls
        logger.debug("Registered agent class: %s", cls.__qualname__)

    @classmethod
    def get_hosted_agent(cls) -> "type[PurposeDrivenAgent]":
        """
        Return the most-derived registered subclass for FAS hosting.

        Priority:
        1. Most-derived class in the registry (longest MRO = most specialised)
        2. cls itself if no subclasses are registered

        This is the fallback when importlib.metadata entry points are unavailable
        (e.g., running from PYTHONPATH rather than as an installed package).
        """
        if not _AGENT_REGISTRY:
            return cls
        return max(_AGENT_REGISTRY.values(), key=lambda c: len(c.__mro__))

    # ── Response post-processing ──────────────────────────────────────────

    def get_routing_tags(self) -> frozenset[str]:
        """
        Return the set of routing tags this agent is allowed to emit.

        Override in subclasses to restrict or extend the tag set.

        Orchestrators override to: {ROUTE:CFO, ROUTE:CMO, COMPLETE}
        Specialists override to:   {HANDBACK}
        """
        return self._routing_tags

    def get_default_routing_tag(self) -> str:
        """
        Return the tag to append when the LLM output contains no routing tag.

        Must be overridden in concrete agent subclasses.
        Raises NotImplementedError if not overridden — forces explicit declaration.
        """
        raise NotImplementedError(
            f"{type(self).__name__} must implement get_default_routing_tag(). "
            "Orchestrators return '[COMPLETE]'; specialists return '[HANDBACK]'."
        )

    def enforce_routing_tag(self, response_text: str) -> str:
        """
        Ensure the response ends with exactly one valid routing tag.

        Algorithm:
        1. Scan the last 120 characters of the response for a known tag.
        2. If found and valid for this agent — return unchanged.
        3. If found but invalid for this agent — replace with default tag.
        4. If not found — append default tag on a new line.

        This method is called by the FAS hosting adapter after every LLM
        response, before the result is returned to the Foundry workflow.

        Args:
            response_text: The raw LLM response string.

        Returns:
            The response string guaranteed to end with a valid routing tag.
        """
        allowed = self.get_routing_tags()
        default = self.get_default_routing_tag()

        # Scan tail of response for any routing tag
        tail = response_text[-120:] if len(response_text) > 120 else response_text
        found_tag: str | None = None
        for tag in self._routing_tags:
            if tag.upper() in tail.upper():
                found_tag = tag
                break

        if found_tag is None:
            # No tag present — append default
            logger.warning(
                "%s LLM output missing routing tag; appending default '%s'",
                type(self).__name__,
                default,
            )
            return response_text.rstrip() + f"\n{default}"

        if found_tag not in allowed:
            # Tag present but not valid for this agent type
            logger.warning(
                "%s emitted disallowed tag '%s'; replacing with '%s'",
                type(self).__name__,
                found_tag,
                default,
            )
            # Replace the disallowed tag with the default
            pattern = re.compile(re.escape(found_tag), re.IGNORECASE)
            return pattern.sub(default, response_text)

        # Valid tag present — return unchanged
        return response_text
```

### 2. `src/purpose_driven_agent/hosting.py` — NEW FILE

Create this file. It is the FAS hosting adapter bridge — the piece that connects `agent-framework-foundry-hosting` to `PurposeDrivenAgent`.

```python
"""
FAS hosting adapter for PurposeDrivenAgent.

Discovers the concrete agent class to host and registers it with the
agent-framework-foundry-hosting server. This module is the entry point
executed by the FAS container CMD.

Discovery order:
1. importlib.metadata entry point group 'agent_framework.hosted_agents', key 'default'
2. PurposeDrivenAgent.get_hosted_agent() registry (most-derived subclass)
3. PurposeDrivenAgent itself as final fallback
"""
from __future__ import annotations

import importlib.metadata
import logging
import os
import sys

logger = logging.getLogger(__name__)


def _discover_agent_class() -> type:
    """
    Discover the concrete agent class to host.

    Returns the class object, not an instance.
    """
    from purpose_driven_agent.agent import PurposeDrivenAgent

    # ── Strategy 1: importlib.metadata entry points ────────────────────────
    entry_point_name = os.environ.get("AGENT_ENTRY_POINT", "default")
    try:
        eps = importlib.metadata.entry_points(group="agent_framework.hosted_agents")
        # entry_points() returns a SelectableGroups object in Python 3.12
        matches = [ep for ep in eps if ep.name == entry_point_name]
        if matches:
            agent_class = matches[0].load()
            logger.info(
                "Discovered agent class via entry point '%s': %s",
                entry_point_name,
                agent_class.__qualname__,
            )
            return agent_class
    except Exception as exc:
        logger.debug("Entry point discovery failed: %s", exc)

    # ── Strategy 2: __init_subclass__ registry ─────────────────────────────
    agent_class = PurposeDrivenAgent.get_hosted_agent()
    if agent_class is not PurposeDrivenAgent:
        logger.info(
            "Discovered agent class via registry: %s",
            agent_class.__qualname__,
        )
        return agent_class

    # ── Strategy 3: PurposeDrivenAgent itself ──────────────────────────────
    logger.warning(
        "No concrete agent subclass found; hosting PurposeDrivenAgent directly. "
        "This is only appropriate for testing — production agents must subclass it."
    )
    return PurposeDrivenAgent


def _ensure_imports() -> None:
    """
    Import the agent package so __init_subclass__ registrations fire.

    In the FAS image, .py files are absent. The .pyc files are discovered
    via SourcelessFileLoader when PYTHONPATH=/app is set. Importing the
    top-level package here triggers all __init_subclass__ calls in the
    class hierarchy, populating the registry before discovery runs.

    This is necessary because importlib.metadata entry points require the
    package to be installed; when running from PYTHONPATH, the registry
    fallback must be seeded by explicit import.
    """
    import importlib
    import pathlib

    app_path = pathlib.Path("/app")

    # Import every top-level package directory found in /app
    # Order: parent layers first (already imported), then leaf packages
    for pkg_dir in sorted(app_path.iterdir()):
        if pkg_dir.is_dir() and not pkg_dir.name.startswith((".", "_")):
            pkg_name = pkg_dir.name
            if pkg_name not in sys.modules:
                try:
                    importlib.import_module(pkg_name)
                    logger.debug("Seeded registry import: %s", pkg_name)
                except ImportError as exc:
                    logger.debug("Could not import %s: %s", pkg_name, exc)


def run_server() -> None:
    """
    Start the FAS hosting server.

    This is the main entry point called from __main__.py.
    It discovers the agent class, instantiates it, and hands it to the
    agent-framework-foundry-hosting server which starts the HTTP listener.
    """
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    logger.info("AOS FAS hosting adapter starting")
    logger.info("PYTHONPATH: %s", os.environ.get("PYTHONPATH", "(not set)"))

    # Seed the __init_subclass__ registry
    _ensure_imports()

    # Discover which agent class to host
    agent_class = _discover_agent_class()
    logger.info("Hosting agent class: %s", agent_class.__qualname__)

    # Instantiate and register with the FAS server
    # The agent-framework-foundry-hosting API:
    #   from azure.ai.agentserver import AgentServer
    #   server = AgentServer()
    #   server.register(agent_instance)
    #   server.serve()
    #
    # If the API differs, adjust the import path. The key contract is:
    # - register() takes an agent instance
    # - serve() starts the HTTP server (blocks)
    try:
        from azure.ai.agentserver import AgentServer  # type: ignore[import]
    except ImportError:
        # Try alternate import path used by some versions of the hosting package
        try:
            from azure.ai.agent_server import AgentServer  # type: ignore[import]
        except ImportError as exc:
            logger.error(
                "Cannot import AgentServer from azure.ai.agentserver or "
                "azure.ai.agent_server. Verify agent-framework-foundry-hosting "
                "is installed in the infrastructure layer. Error: %s",
                exc,
            )
            sys.exit(1)

    agent_instance = agent_class()
    server = AgentServer()
    server.register(agent_instance)

    port = int(os.environ.get("AGENT_SERVICE_PORT", "8000"))
    logger.info("Starting FAS server on port %d", port)
    server.serve(port=port)
```

### 3. `src/purpose_driven_agent/__main__.py` — NEW FILE

This is what `CMD ["python", "-m", "purpose_driven_agent"]` executes in the container.

```python
"""
Entry point for running purpose_driven_agent as a FAS hosted container.

Executed by:
    CMD ["python", "-m", "purpose_driven_agent"]

or equivalently:
    python -m purpose_driven_agent
"""
from purpose_driven_agent.hosting import run_server

if __name__ == "__main__":
    run_server()
```

### 4. `src/purpose_driven_agent/routing_mixin.py` — NEW FILE

A mixin that concrete agent subclasses use to declare their routing role. Separates routing concerns from agent logic.

```python
"""
RoutingMixin — declares an agent's role in the routing protocol.

Usage:
    class FounderAgent(RoutingMixin, BusinessAgent):
        ROUTING_ROLE = "orchestrator"
        # get_default_routing_tag() returns "[COMPLETE]"

    class CFOAgent(RoutingMixin, BusinessAgent):
        ROUTING_ROLE = "specialist"
        # get_default_routing_tag() returns "[HANDBACK]"
"""
from __future__ import annotations

from typing import ClassVar, Literal

_ORCHESTRATOR_TAGS = frozenset({"[ROUTE:CFO]", "[ROUTE:CMO]", "[COMPLETE]"})
_SPECIALIST_TAGS = frozenset({"[HANDBACK]"})


class RoutingMixin:
    """
    Mixin that configures the routing tag enforcement in PurposeDrivenAgent.

    Must be mixed in before PurposeDrivenAgent in the MRO:
        class FounderAgent(RoutingMixin, BusinessAgent): ...
    where BusinessAgent inherits from PurposeDrivenAgent.

    Attributes:
        ROUTING_ROLE: "orchestrator" or "specialist".
            orchestrators emit [ROUTE:CFO], [ROUTE:CMO], or [COMPLETE]
            specialists emit [HANDBACK]
    """

    ROUTING_ROLE: ClassVar[Literal["orchestrator", "specialist"]] = "orchestrator"

    def get_routing_tags(self) -> frozenset[str]:
        if self.ROUTING_ROLE == "specialist":
            return _SPECIALIST_TAGS
        return _ORCHESTRATOR_TAGS

    def get_default_routing_tag(self) -> str:
        if self.ROUTING_ROLE == "specialist":
            return "[HANDBACK]"
        return "[COMPLETE]"
```

---

## Required Changes to `src/aos_mcp_servers/routing.py`

This file already exists (imported by `purpose_driven_agent.agent`). It needs the `RoutingClassifier` class added — the stateless classifier that the `enforce_routing_tag` method in `PurposeDrivenAgent` calls internally.

> **Do not replace the existing file.** Add the `RoutingClassifier` class alongside whatever is already there.

```python
# Add to src/aos_mcp_servers/routing.py

import re
from typing import Final

# All known routing tags — canonical uppercase form
ROUTING_TAGS: Final[frozenset[str]] = frozenset(
    {"[ROUTE:CFO]", "[ROUTE:CMO]", "[COMPLETE]", "[HANDBACK]"}
)

# Scan window: only inspect this many characters from the end of a response
_TAIL_CHARS: Final[int] = 120

# Pattern matching any routing tag (case-insensitive)
_TAG_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"\[(ROUTE:CFO|ROUTE:CMO|COMPLETE|HANDBACK)\]",
    re.IGNORECASE,
)


class RoutingClassifier:
    """
    Stateless classifier that detects routing tags in LLM response text.

    This class is intentionally stateless — all state lives in the agent.
    It can be used as a utility from any layer in the hierarchy.
    """

    @staticmethod
    def extract_tag(response_text: str) -> str | None:
        """
        Return the routing tag found in the response tail, or None.

        Scans only the last _TAIL_CHARS characters for efficiency.
        Returns the tag in canonical uppercase form (e.g., '[ROUTE:CFO]').
        """
        tail = response_text[-_TAIL_CHARS:] if len(response_text) > _TAIL_CHARS else response_text
        match = _TAG_PATTERN.search(tail)
        if match:
            return f"[{match.group(1).upper()}]"
        return None

    @staticmethod
    def has_tag(response_text: str) -> bool:
        """Return True if any routing tag is present in the response tail."""
        return RoutingClassifier.extract_tag(response_text) is not None

    @staticmethod
    def is_route_tag(tag: str) -> bool:
        """Return True if the tag is a [ROUTE:*] tag (not COMPLETE or HANDBACK)."""
        return tag.upper().startswith("[ROUTE:")

    @staticmethod
    def route_target(tag: str) -> str | None:
        """
        Extract the specialist name from a [ROUTE:X] tag.

        Returns 'CFO', 'CMO', etc., or None if not a route tag.
        """
        match = re.match(r"\[ROUTE:([A-Z]+)\]", tag.upper())
        return match.group(1) if match else None
```

---

## Required Changes to `pyproject.toml`

Update the existing `pyproject.toml` with these changes. The file already has the correct structure — these are targeted additions.

### 1. Update `requires-python` and classifiers

```toml
requires-python = ">=3.12"

classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: Apache Software License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.12",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
    "Framework :: AsyncIO",
]
```

### 2. Update `dependencies` version pins

```toml
dependencies = [
    "agent-framework>=1.3.0",
    "agent-framework-foundry>=1.3.0",
    "azure-ai-agents>=1.1.0",
    "azure-identity>=1.21.0",
    "pydantic>=2.13.0",
]
```

### 3. Add entry point declaration

```toml
[project.entry-points."agent_framework.hosted_agents"]
default = "purpose_driven_agent.agent:PurposeDrivenAgent"
```

This declares `PurposeDrivenAgent` as the default hosted agent. Leaf agent repos (e.g., `founder-agent`) override this with their own `pyproject.toml` entry pointing to their concrete class.

### 4. Verify `packages` includes both packages

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/purpose_driven_agent", "src/aos_mcp_servers"]
```

This is already correct per the existing file — confirm it's unchanged.

---

## Required Changes to `Dockerfile.purpose-driven-agent`

The Dockerfile already exists in the repo. The following changes are needed.

### Change 1: Add `PYTHONPATH` env var to the `base` stage

Add immediately after `WORKDIR /app`:

```dockerfile
ENV PYTHONPATH=/app
```

Without this, `python -m purpose_driven_agent` fails to find sibling packages (`aos_mcp_servers`) when the container starts.

### Change 2: Ensure both packages are copied and compiled together

The existing Dockerfile already has:
```dockerfile
COPY --chown=aosuser:aosuser src/purpose_driven_agent/ ./purpose_driven_agent/
COPY --chown=aosuser:aosuser src/aos_mcp_servers/ ./aos_mcp_servers/

USER aosuser

RUN python -m compileall -b -j0 -q ./purpose_driven_agent/ ./aos_mcp_servers/
```

Confirm `-b` flag is present. If not, add it. This is required for SourcelessFileLoader.

### Change 3: Update smoke test to verify hosting module

```dockerfile
RUN python -c "from purpose_driven_agent import PurposeDrivenAgent; \
from purpose_driven_agent.hosting import _discover_agent_class; \
from aos_mcp_servers.routing import RoutingClassifier; \
print('Layer 2 smoke test passed.')"
```

### Change 4: Update CMD to use module execution

```dockerfile
CMD ["python", "-m", "purpose_driven_agent"]
```

This invokes `src/purpose_driven_agent/__main__.py` → `run_server()`.

### Change 5: FAS stage — verify both packages are stripped

```dockerfile
FROM base AS fas

RUN find /app/purpose_driven_agent /app/aos_mcp_servers -name "*.py" -delete

RUN python -c "\
import pathlib; \
pyc = list(pathlib.Path('/app').rglob('*.pyc')); \
py  = list(pathlib.Path('/app/purpose_driven_agent').rglob('*.py')) + \
      list(pathlib.Path('/app/aos_mcp_servers').rglob('*.py')); \
assert len(pyc) > 0, 'No .pyc files found'; \
assert len(py)  == 0, f'Found .py in FAS image: {py}'; \
print(f'FAS stage: {len(pyc)} .pyc, 0 .py. OK') \
"

USER aosuser
CMD ["python", "-m", "purpose_driven_agent"]
```

---

## Required Changes to `.gitignore`

Add to root `.gitignore` if not already present:

```
__pycache__/
*.py[cod]
*.pyo
```

This prevents compiled artifacts from being committed, which caused permission errors during `compileall` in prior builds.

---

## File Summary

| File | Action | Description |
|---|---|---|
| `src/purpose_driven_agent/agent.py` | Modify | Add `__init_subclass__` registry, `get_hosted_agent()`, `get_routing_tags()`, `get_default_routing_tag()`, `enforce_routing_tag()` |
| `src/purpose_driven_agent/hosting.py` | Create | FAS adapter — entry point discovery, `run_server()` |
| `src/purpose_driven_agent/__main__.py` | Create | `python -m purpose_driven_agent` entry point |
| `src/purpose_driven_agent/routing_mixin.py` | Create | `RoutingMixin` for orchestrator/specialist role declaration |
| `src/aos_mcp_servers/routing.py` | Modify | Add `RoutingClassifier`, `ROUTING_TAGS`, constants |
| `pyproject.toml` | Modify | Update Python version, deps, add entry point group |
| `Dockerfile.purpose-driven-agent` | Modify | Add `ENV PYTHONPATH`, confirm `-b` flag, update smoke test, update `CMD` |
| `.gitignore` | Modify | Add `__pycache__/`, `*.py[cod]` |

---

## Validation Checklist

The coding agent must verify all of the following after making changes:

- [ ] `python -m compileall -b -j0 ./src/purpose_driven_agent/ ./src/aos_mcp_servers/` succeeds with no errors
- [ ] `python -c "from purpose_driven_agent.agent import PurposeDrivenAgent; print(PurposeDrivenAgent.get_hosted_agent())"` prints `<class 'purpose_driven_agent.agent.PurposeDrivenAgent'>`
- [ ] `python -c "from aos_mcp_servers.routing import RoutingClassifier; assert RoutingClassifier.extract_tag('hello [ROUTE:CFO]') == '[ROUTE:CFO]'"` passes
- [ ] `python -c "from purpose_driven_agent.routing_mixin import RoutingMixin; print('OK')"` passes
- [ ] `python -c "from purpose_driven_agent.hosting import _discover_agent_class; print(_discover_agent_class())"` prints the `PurposeDrivenAgent` class
- [ ] After simulating the FAS strip (`find . -name "*.py" -delete`), `python -c "from purpose_driven_agent.agent import PurposeDrivenAgent"` still succeeds (via `.pyc` files)
- [ ] Routing tag enforcement: `PurposeDrivenAgent().enforce_routing_tag("some text")` returns text ending with `"\n[COMPLETE]"` (after implementing `get_default_routing_tag` in a concrete subclass)
- [ ] `pyproject.toml` entry point `agent_framework.hosted_agents:default` resolves to `PurposeDrivenAgent`
