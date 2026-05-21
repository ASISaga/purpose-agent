from __future__ import annotations

import logging
from typing import Optional

from purpose_driven_agent.context_providers.subconscious_context_provider import (
    SubconsciousContextProvider,
)
from purpose_driven_agent.context_providers.subconscious_schema_context_provider import (
    SubconsciousSchemaContextProvider,
)


#: Base URL of the live ASI Saga subconscious MCP server.
SUBCONSCIOUS_MCP_URL: str = "https://subconscious.asisaga.com/mcp"


def create_subconscious_provider(
    orchestration_id: str,
    tool_name: str = "get_conversation",
    limit: int = 200,
    mcp_url: str = SUBCONSCIOUS_MCP_URL,
) -> SubconsciousContextProvider:
    """Create a :class:`SubconsciousContextProvider` wired to the live
    ``subconscious.asisaga.com`` MCP server.

    Uses ``agent_framework.MCPStreamableHTTPTool`` (the real Microsoft Agent
    Framework HTTP transport) wrapped in an
    :class:`~aos_mcp_servers.routing.AgentFrameworkMCPServerAdapter` that
    adapts its ``**kwargs`` calling convention to the
    :class:`~purpose_driven_agent.MCPServerProtocol` interface expected by
    :class:`SubconsciousContextProvider`.

    Example::

        from purpose_driven_agent import GenericPurposeDrivenAgent
        from purpose_driven_agent.context_provider import create_subconscious_provider

        agent = GenericPurposeDrivenAgent(
            agent_id="cmo",
            purpose="Lead marketing strategy and brand growth",
            adapter_name="marketing",
        )
        await agent.initialize()
        agent.set_context_provider(
            create_subconscious_provider(orchestration_id="orch-cmo-2026-q2")
        )
        result = await agent.handle_event({"type": "strategy_review"})
        # result["injected_context"] == "CONVERSATION HISTORY:\\n..."

    Args:
        orchestration_id: Unique identifier for the orchestration whose
            conversation history to retrieve and persist
            (e.g. ``"orch-cmo-2026-q2"``).  Forwarded to the MCP tools
            as ``orchestration_id``.
        tool_name: Name of the MCP retrieval tool to invoke.  Defaults to
            ``"get_conversation"``.
        limit: Maximum number of messages to retrieve per call.  Defaults to
            ``200``.
        mcp_url: Base URL of the MCP server.  Defaults to
            :data:`SUBCONSCIOUS_MCP_URL` (``https://subconscious.asisaga.com/mcp``).

    Returns:
        A :class:`SubconsciousContextProvider` that connects to the live
        ``subconscious.asisaga.com`` server on first use.

    Raises:
        ImportError: If ``agent_framework`` is not installed.  Install it with
            ``pip install agent-framework`` or ``pip install purpose-driven-agent[azure]``.
    """
    try:
        from agent_framework import MCPStreamableHTTPTool
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "agent-framework is required for create_subconscious_provider(). "
            "Install it with: pip install agent-framework"
        ) from exc

    from purpose_driven_agent._aos_mcp_servers.routing import AgentFrameworkMCPServerAdapter

    real_tool = MCPStreamableHTTPTool(
        name="subconscious",
        url=mcp_url,
    )
    adapter: Optional[AgentFrameworkMCPServerAdapter] = AgentFrameworkMCPServerAdapter(real_tool)

    logger = logging.getLogger("purpose_driven_agent.create_subconscious_provider")
    logger.info(
        "Created SubconsciousContextProvider for orchestration '%s' → %s",
        orchestration_id,
        mcp_url,
    )

    return SubconsciousContextProvider(
        mcp_server=adapter,
        orchestration_id=orchestration_id,
        tool_name=tool_name,
        limit=limit,
    )


def create_subconscious_schema_provider(
    schema_name: str,
    context_id: str,
    mcp_url: str = SUBCONSCIOUS_MCP_URL,
) -> "SubconsciousSchemaContextProvider":
    """Create a :class:`SubconsciousSchemaContextProvider` wired to the live
    ``subconscious.asisaga.com`` MCP server.

    Uses ``agent_framework.MCPStreamableHTTPTool`` (the real Microsoft Agent
    Framework HTTP transport) wrapped in an
    :class:`~aos_mcp_servers.routing.AgentFrameworkMCPServerAdapter` that
    adapts its ``**kwargs`` calling convention to the
    :class:`~purpose_driven_agent.MCPServerProtocol` interface expected by
    :class:`SubconsciousSchemaContextProvider`.

    The returned provider reads and writes JSON-LD mind-schema documents
    (Manas, Buddhi, Ahankara, Chitta, and entity perspectives) stored in
    Azure Table Storage on the subconscious MCP server.

    Example::

        from purpose_driven_agent import GenericPurposeDrivenAgent
        from purpose_driven_agent.context_provider import (
            create_subconscious_schema_provider,
        )

        agent = GenericPurposeDrivenAgent(
            agent_id="cmo",
            purpose="Lead marketing strategy and brand growth",
            adapter_name="marketing",
        )
        await agent.initialize()
        agent.set_context_provider(
            create_subconscious_schema_provider(schema_name="manas", context_id="cmo")
        )

        # handle_event fetches the Manas document and injects it as context
        result = await agent.handle_event({"type": "strategy_review"})
        # result["injected_context"] == "SCHEMA CONTEXT (manas):\\n..."

        # Persist the updated Manas document after processing:
        schema_provider = agent.context_provider
        await schema_provider.store_schema_context(updated_manas_document)

    Args:
        schema_name: Name of the mind schema to work with.  Must be one of
            ``"manas"``, ``"buddhi"``, ``"ahankara"``, ``"chitta"``,
            ``"action-plan"``, ``"entity-context"``, or ``"entity-content"``.
        context_id: Unique identifier for the schema context document
            (e.g. the agent's ID ``"cmo"``).
        mcp_url: Base URL of the MCP server.  Defaults to
            :data:`SUBCONSCIOUS_MCP_URL` (``https://subconscious.asisaga.com/mcp``).

    Returns:
        A :class:`SubconsciousSchemaContextProvider` that connects to the live
        ``subconscious.asisaga.com`` server on first use.

    Raises:
        ImportError: If ``agent_framework`` is not installed.  Install it with
            ``pip install agent-framework`` or ``pip install purpose-driven-agent[azure]``.
    """
    try:
        from agent_framework import MCPStreamableHTTPTool
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "agent-framework is required for create_subconscious_schema_provider(). "
            "Install it with: pip install agent-framework"
        ) from exc

    from purpose_driven_agent._aos_mcp_servers.routing import AgentFrameworkMCPServerAdapter

    real_tool = MCPStreamableHTTPTool(
        name="subconscious",
        url=mcp_url,
    )
    adapter: Optional[AgentFrameworkMCPServerAdapter] = AgentFrameworkMCPServerAdapter(real_tool)

    logger = logging.getLogger("purpose_driven_agent.create_subconscious_schema_provider")
    logger.info(
        "Created SubconsciousSchemaContextProvider for schema '%s' context '%s' → %s",
        schema_name,
        context_id,
        mcp_url,
    )

    return SubconsciousSchemaContextProvider(
        mcp_server=adapter,
        schema_name=schema_name,
        context_id=context_id,
    )
