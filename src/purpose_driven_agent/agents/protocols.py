from __future__ import annotations

from typing import Any, Dict, List, Protocol

from purpose_driven_agent._aos_mcp_servers.routing import MCPToolDefinition


class MCPServerProtocol(Protocol):
    """
    Structural protocol for MCP servers registered with :class:`PurposeDrivenAgent`.

    Any object that provides ``call_tool`` and ``list_tools`` async methods
    satisfies this protocol and can be registered via
    :meth:`PurposeDrivenAgent.register_mcp_server`.

    The three concrete transport classes —
    :class:`~purpose_driven_agent._aos_mcp_servers.routing.MCPStdioTool`,
    :class:`~purpose_driven_agent._aos_mcp_servers.routing.MCPStreamableHTTPTool`,
    and :class:`~purpose_driven_agent._aos_mcp_servers.routing.MCPWebsocketTool`
    — all satisfy this protocol. They are internal to ``purpose_driven_agent``.

    The :class:`~aos_client.mcp.MCPServerConfig` Pydantic model (from
    ``aos-client-sdk``) describes these servers declaratively for use in
    :class:`~aos_client.models.OrchestrationRequest`, letting clients select
    which MCP servers each agent should connect to.
    """

    async def list_tools(self) -> List[MCPToolDefinition]:
        """
        Return the :class:`MCPToolDefinition` objects available on this server.

        Called by :meth:`~PurposeDrivenAgent.discover_mcp_tools` to build the
        tool-name → server-name routing index.

        Returns:
            List of
            :class:`~purpose_driven_agent._aos_mcp_servers.routing.MCPToolDefinition`
            objects.
        """
        ...  # pragma: no cover

    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """Invoke *tool_name* with *params* and return the result."""
        ...  # pragma: no cover


class AOSProtocol(Protocol):
    """Minimal protocol used by persona helper methods."""

    def get_available_personas(self) -> List[str]:
        """Return available persona names."""
        ...

    def validate_personas(self, personas: List[str]) -> bool:
        """Validate that persona names are available."""
        ...
