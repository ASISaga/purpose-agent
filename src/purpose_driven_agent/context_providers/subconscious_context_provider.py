from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from purpose_driven_agent.context_providers.context import Context
from purpose_driven_agent.context_providers.provider import ContextProvider


class SubconsciousContextProvider(ContextProvider):
    """ContextProvider backed by the ``subconscious.asisaga.com`` MCP server.

    Implements the Context Pipeline described in ``pr/context.md``:

    **Reading (context injection)**

    1. Calls ``get_conversation`` (or a configured tool name) on the registered
       MCP server, passing the orchestration ID and an optional message limit.
    2. Normalises the raw output to a string (handles both ``dict`` and ``str``
       results).
    3. Engineers it into a ``CONVERSATION HISTORY`` instruction block.
    4. Returns a :class:`Context` with the instruction block and the
       passed-through messages.

    **Writing (message persistence)**

    Exposes :meth:`persist_message` and :meth:`persist_conversation_turn` so
    that the orchestrating agent can write new messages back to the server
    after processing an event.

    The MCP server uses the ``orchestration_id`` to isolate each agent's
    conversation, enabling a single server to serve all 15+ repos in the ASI
    Saga ecosystem.

    Example::

        from purpose_driven_agent.context_provider import create_subconscious_provider

        provider = create_subconscious_provider(orchestration_id="orch-cmo-2026-q2")
        context = await provider.get_context(messages=[])
        # context.instructions == "CONVERSATION HISTORY:\\n..."

        # Persist a new message after the agent responds:
        await provider.persist_message(
            agent_id="cmo",
            role="assistant",
            content="Marketing strategy reviewed.",
        )
    """

    def __init__(
        self,
        mcp_server: Any,
        orchestration_id: str,
        tool_name: str = "get_conversation",
        limit: int = 200,
    ) -> None:
        """Initialise the SubconsciousContextProvider.

        Args:
            mcp_server: MCP server instance that exposes the subconscious
                tools.  Must implement ``async call_tool(tool_name, params)``
                (satisfies :class:`~purpose_driven_agent.MCPServerProtocol`).
            orchestration_id: Unique identifier for the orchestration whose
                conversation history to retrieve and persist.  Passed to the
                MCP tools as ``orchestration_id``.
            tool_name: Name of the MCP retrieval tool to invoke.  Defaults to
                ``"get_conversation"``.
            limit: Maximum number of messages to retrieve per call.  Defaults
                to ``200``.
        """
        self.mcp_server = mcp_server
        self.orchestration_id = orchestration_id
        self.tool_name = tool_name
        self.limit = limit
        self.logger = logging.getLogger(
            f"purpose_driven_agent.SubconsciousContextProvider.{orchestration_id}"
        )

    async def get_context(
        self,
        messages: List[Dict[str, Any]],
        **kwargs: Any,
    ) -> Context:
        """Fetch conversation history and engineer it into a Context object.

        Calls :attr:`tool_name` on :attr:`mcp_server` with this orchestration's
        ID and the configured :attr:`limit`.  The raw output is normalised to a
        string and formatted as a ``CONVERSATION HISTORY`` block.

        If the MCP call fails, an empty instruction string is returned so
        the agent can continue operating in a degraded mode rather than
        raising an exception.

        Args:
            messages: Conversation messages passed through to the returned
                :class:`Context` unchanged.
            **kwargs: Not used; present for interface compatibility.

        Returns:
            :class:`Context` with the engineered conversation history
            instruction block and the passed-through messages.
        """
        try:
            raw_output = await self.mcp_server.call_tool(
                self.tool_name,
                {"orchestration_id": self.orchestration_id, "limit": self.limit},
            )
            # Normalise to string — MCP tools may return dict, list, or str
            if isinstance(raw_output, (dict, list)):
                raw_content = json.dumps(raw_output)
            else:
                raw_content = str(raw_output)

            engineered_context = f"CONVERSATION HISTORY:\n{raw_content}"
            self.logger.debug(
                "SubconsciousContextProvider fetched context for orchestration '%s'",
                self.orchestration_id,
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.logger.error(
                "Failed to fetch subconscious context for orchestration '%s': %s",
                self.orchestration_id,
                exc,
            )
            engineered_context = ""

        return Context(instructions=engineered_context, messages=messages)

    async def persist_message(
        self,
        agent_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Append a single message to this orchestration's conversation.

        Calls the ``persist_message`` tool on :attr:`mcp_server`.  If the
        call fails, the error is logged and ``None`` is returned so that the
        agent can continue without interruption.

        Args:
            agent_id: Identifier of the agent producing the message
                (e.g. ``"cmo"``).
            role: Message role — ``"user"``, ``"assistant"``, ``"system"``,
                or ``"tool"``.
            content: Full text content of the message.
            metadata: Optional structured metadata dict (serialised as JSON
                by the server).

        Returns:
            Confirmation dict from the server (with ``sequence`` and
            ``timestamp`` keys), or ``None`` on failure.
        """
        try:
            return await self.mcp_server.call_tool(
                "persist_message",
                {
                    "orchestration_id": self.orchestration_id,
                    "agent_id": agent_id,
                    "role": role,
                    "content": content,
                    "metadata": metadata,
                },
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.logger.error(
                "Failed to persist message for orchestration '%s': %s",
                self.orchestration_id,
                exc,
            )
            return None

    async def persist_conversation_turn(
        self,
        messages: List[Dict[str, Any]],
    ) -> Any:
        """Persist multiple messages for one orchestration turn in a single call.

        Each element in *messages* must contain ``agent_id``, ``role``, and
        ``content`` keys, with an optional ``metadata`` dict.  Calls the
        ``persist_conversation_turn`` tool on :attr:`mcp_server`.

        Args:
            messages: List of message dicts to persist.

        Returns:
            Summary dict from the server (with ``persisted`` count), or
            ``None`` on failure.
        """
        try:
            return await self.mcp_server.call_tool(
                "persist_conversation_turn",
                {
                    "orchestration_id": self.orchestration_id,
                    "messages": messages,
                },
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.logger.error(
                "Failed to persist conversation turn for orchestration '%s': %s",
                self.orchestration_id,
                exc,
            )
            return None

    async def create_orchestration(
        self,
        purpose: str,
        agents: Optional[List[str]] = None,
    ) -> Any:
        """Register this orchestration on the subconscious MCP server.

        Calls ``create_orchestration`` with :attr:`orchestration_id` and the
        given *purpose*.  Should be called once before the first
        :meth:`get_context` or :meth:`persist_message` call.  If the
        orchestration already exists the server is expected to return it
        without error.

        Args:
            purpose: Human-readable purpose for this orchestration
                (e.g. ``"Q2 marketing strategy review"``).
            agents: Optional list of agent IDs that participate in this
                orchestration (e.g. ``["cmo", "cfo"]``).

        Returns:
            Orchestration record dict from the server, or ``None`` on failure.
        """
        try:
            return await self.mcp_server.call_tool(
                "create_orchestration",
                {
                    "orchestration_id": self.orchestration_id,
                    "purpose": purpose,
                    "agents": agents,
                },
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.logger.error(
                "Failed to create orchestration '%s': %s",
                self.orchestration_id,
                exc,
            )
            return None

    async def list_orchestrations(
        self,
        status: Optional[str] = None,
    ) -> Any:
        """List all orchestrations on the subconscious MCP server.

        Calls ``list_orchestrations``.  The result is not filtered by
        :attr:`orchestration_id` — it returns all orchestrations, optionally
        filtered by *status*.

        Args:
            status: Optional status filter (e.g. ``"active"`` or
                ``"completed"``).  When ``None``, all orchestrations are
                returned.

        Returns:
            List of orchestration record dicts from the server, or ``None``
            on failure.
        """
        try:
            return await self.mcp_server.call_tool(
                "list_orchestrations",
                {"status": status},
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.logger.error("Failed to list orchestrations: %s", exc)
            return None

    async def complete_orchestration(
        self,
        summary: Optional[str] = None,
    ) -> Any:
        """Mark this orchestration as completed on the subconscious MCP server.

        Calls ``complete_orchestration`` with :attr:`orchestration_id`.

        Args:
            summary: Optional human-readable summary of the orchestration
                outcome.

        Returns:
            Updated orchestration record from the server, or ``None`` on
            failure.
        """
        try:
            return await self.mcp_server.call_tool(
                "complete_orchestration",
                {
                    "orchestration_id": self.orchestration_id,
                    "summary": summary,
                },
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.logger.error(
                "Failed to complete orchestration '%s': %s",
                self.orchestration_id,
                exc,
            )
            return None
