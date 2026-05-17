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
            return agent_class  # type: ignore[return-value]
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
