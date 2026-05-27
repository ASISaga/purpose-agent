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
    """
    PEP 544 structural protocol defining the interface any AOS agent must satisfy.

    Used for static type checking across the hierarchy — not for runtime
    ``isinstance`` checks.  Any class that provides all four methods satisfies
    this protocol.

    | Method | Contract |
    |---|---|
    | ``get_routing_tags()`` | Returns ``frozenset[str]`` of valid routing tags |
    | ``get_default_routing_tag()`` | Returns ``str`` — default tag when none present |
    | ``enforce_routing_tag(response_text)`` | Returns ``str`` — response with guaranteed valid tag |
    | ``run_turn(session)`` | Returns ``TurnResult`` — one LLM call, deterministic lifecycle |
    """

    def get_routing_tags(self) -> frozenset[str]:
        """Return the set of valid routing tags for this agent."""
        ...  # pragma: no cover

    def get_default_routing_tag(self) -> str:
        """Return the default routing tag to append when the LLM emits none."""
        ...  # pragma: no cover

    def enforce_routing_tag(self, response_text: str) -> str:
        """Return *response_text* guaranteed to end with exactly one valid routing tag."""
        ...  # pragma: no cover

    async def run_turn(self, session: Any) -> Any:
        """Execute one deterministic agent turn and return a TurnResult."""
        ...  # pragma: no cover


class PersonaCallbackProtocol(Protocol):
    """
    Structural protocol for objects that expose persona query callbacks.

    Previously embedded in ``AOSProtocol``; extracted here so that objects
    implementing persona resolution (e.g. the AgentOperatingSystem) can be
    typed separately from the agent interaction interface.
    """

    def get_available_personas(self) -> List[str]:
        """Return available persona names."""
        ...  # pragma: no cover

    def validate_personas(self, personas: List[str]) -> bool:
        """Validate that persona names are available."""
        ...  # pragma: no cover

