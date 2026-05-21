from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from purpose_driven_agent.context_providers.context import Context
from purpose_driven_agent.context_providers.provider import ContextProvider


class SubconsciousSchemaContextProvider(ContextProvider):
    """ContextProvider backed by the ``subconscious.asisaga.com`` schema context store.

    Manages **JSON-LD mind-schema documents** (Manas, Buddhi, Ahankara, Chitta,
    and entity perspectives) stored in the subconscious MCP server.

    **Reading (context injection)**

    :meth:`get_context` calls ``get_schema_context`` on the registered MCP
    server, passing ``schema_name`` and ``context_id``.  The raw output is
    normalised to a string and engineered into a ``SCHEMA CONTEXT``
    instruction block injected into the agent's LLM reasoning loop.

    **Writing (schema context persistence)**

    :meth:`store_schema_context` calls ``store_schema_context`` on the MCP
    server to persist an updated JSON-LD mind document back to Azure Table
    Storage.  :meth:`list_schema_contexts` calls ``list_schema_contexts`` to
    enumerate available contexts for this schema.

    Example::

        from purpose_driven_agent.context_provider import (
            create_subconscious_schema_provider,
        )

        provider = create_subconscious_schema_provider(
            schema_name="manas",
            context_id="cmo",
        )

        # Inject Manas document into the agent's reasoning loop:
        context = await provider.get_context(messages=[])
        # context.instructions == "SCHEMA CONTEXT (manas):\\n..."

        # Persist an updated Manas document after the agent processes an event:
        await provider.store_schema_context(updated_manas_document)
    """

    def __init__(
        self,
        mcp_server: Any,
        schema_name: str,
        context_id: str,
    ) -> None:
        """Initialise the SubconsciousSchemaContextProvider.

        Args:
            mcp_server: MCP server instance that exposes the subconscious
                schema context tools.  Must implement
                ``async call_tool(tool_name, params)``
                (satisfies :class:`~purpose_driven_agent.MCPServerProtocol`).
            schema_name: Name of the mind schema to work with.  Must be one
                of ``"manas"``, ``"buddhi"``, ``"ahankara"``, ``"chitta"``,
                ``"action-plan"``, ``"entity-context"``, or
                ``"entity-content"``.
            context_id: Unique identifier for the schema context document to
                retrieve and persist.  Typically the agent's ID
                (e.g. ``"cmo"``).
        """
        self.mcp_server = mcp_server
        self.schema_name = schema_name
        self.context_id = context_id
        self.logger = logging.getLogger(
            f"purpose_driven_agent.SubconsciousSchemaContextProvider"
            f".{schema_name}.{context_id}"
        )

    async def get_context(
        self,
        messages: List[Dict[str, Any]],
        **kwargs: Any,
    ) -> Context:
        """Fetch the schema context document and engineer it into a Context object.

        Calls ``get_schema_context`` on :attr:`mcp_server` with
        :attr:`schema_name` and :attr:`context_id`.  The raw output is
        normalised to a string and formatted as a ``SCHEMA CONTEXT`` block.

        If the MCP call fails, an empty instruction string is returned so
        the agent can continue operating in a degraded mode rather than
        raising an exception.

        Args:
            messages: Conversation messages passed through to the returned
                :class:`Context` unchanged.
            **kwargs: Not used; present for interface compatibility.

        Returns:
            :class:`Context` with the engineered schema context instruction
            block and the passed-through messages.
        """
        try:
            raw_output = await self.mcp_server.call_tool(
                "get_schema_context",
                {"schema_name": self.schema_name, "context_id": self.context_id},
            )
            # Normalise to string — MCP tools may return dict, list, or str
            if isinstance(raw_output, (dict, list)):
                raw_content = json.dumps(raw_output)
            else:
                raw_content = str(raw_output)

            engineered_context = f"SCHEMA CONTEXT ({self.schema_name}):\n{raw_content}"
            self.logger.debug(
                "SubconsciousSchemaContextProvider fetched '%s' context for id '%s'",
                self.schema_name,
                self.context_id,
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.logger.error(
                "Failed to fetch schema context '%s/%s': %s",
                self.schema_name,
                self.context_id,
                exc,
            )
            engineered_context = ""

        return Context(instructions=engineered_context, messages=messages)

    async def get_schema_context(self) -> Any:
        """Retrieve the raw schema context document from the MCP server.

        Calls ``get_schema_context`` on :attr:`mcp_server` with
        :attr:`schema_name` and :attr:`context_id` and returns the raw
        output without any formatting.

        Returns:
            Raw schema context document returned by the MCP server (typically
            a ``dict`` for a JSON-LD document), or ``None`` on failure.
        """
        try:
            return await self.mcp_server.call_tool(
                "get_schema_context",
                {"schema_name": self.schema_name, "context_id": self.context_id},
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.logger.error(
                "Failed to get schema context '%s/%s': %s",
                self.schema_name,
                self.context_id,
                exc,
            )
            return None

    async def store_schema_context(self, document: Any) -> Any:
        """Persist a JSON-LD schema context document to the MCP server.

        Calls ``store_schema_context`` on :attr:`mcp_server` with
        :attr:`schema_name`, :attr:`context_id`, and the provided *document*.
        If the call fails, the error is logged and ``None`` is returned so
        that the agent can continue without interruption.

        Args:
            document: JSON-LD document conforming to the schema identified
                by :attr:`schema_name`.  Typically a ``dict`` following the
                mind-schema structure (e.g. Manas, Buddhi).

        Returns:
            Confirmation payload from the server, or ``None`` on failure.
        """
        try:
            return await self.mcp_server.call_tool(
                "store_schema_context",
                {
                    "schema_name": self.schema_name,
                    "context_id": self.context_id,
                    "document": document,
                },
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.logger.error(
                "Failed to store schema context '%s/%s': %s",
                self.schema_name,
                self.context_id,
                exc,
            )
            return None

    async def list_schema_contexts(self) -> Any:
        """List stored schema contexts for this schema from the MCP server.

        Calls ``list_schema_contexts`` on :attr:`mcp_server`, filtered by
        :attr:`schema_name`.  If the call fails, the error is logged and
        ``None`` is returned.

        Returns:
            List of available schema context descriptors from the server,
            or ``None`` on failure.
        """
        try:
            return await self.mcp_server.call_tool(
                "list_schema_contexts",
                {"schema_name": self.schema_name},
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.logger.error(
                "Failed to list schema contexts for '%s': %s",
                self.schema_name,
                exc,
            )
            return None

    async def get_schema(self) -> Any:
        """Retrieve the JSON Schema definition for this schema from the MCP server.

        Calls ``get_schema`` on :attr:`mcp_server` with :attr:`schema_name`.
        This returns the *schema definition* (the JSON Schema document that
        describes valid mind documents), not a stored context document.

        Returns:
            Schema definition dict from the server, or ``None`` on failure.
        """
        try:
            return await self.mcp_server.call_tool(
                "get_schema",
                {"schema_name": self.schema_name},
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.logger.error(
                "Failed to get schema definition for '%s': %s",
                self.schema_name,
                exc,
            )
            return None

    async def list_schemas(self) -> Any:
        """List all available mind-schema names from the MCP server.

        Calls ``list_schemas`` on :attr:`mcp_server`.  Returns the names of
        all schema definitions hosted by the server (e.g. ``"manas"``,
        ``"buddhi"``, ``"ahankara"``, ``"chitta"``, ``"action-plan"``,
        ``"entity-context"``, ``"entity-content"``).

        Returns:
            List of schema name strings (or dicts with metadata), or
            ``None`` on failure.
        """
        try:
            return await self.mcp_server.call_tool("list_schemas", {})
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.logger.error("Failed to list schemas: %s", exc)
            return None

    async def initialize_schema_contexts(self, force: bool = False) -> Any:
        """Bootstrap schema contexts from the repository's mind-schema files.

        Calls ``initialize_schema_contexts`` on :attr:`mcp_server`.  This
        one-time operation reads the JSON-LD seed documents from the
        ``boardroom/mind/`` directory in the ``subconscious.asisaga.com``
        repository and populates the ``SchemaContexts`` Azure Table with
        initial agent context documents.

        Should be called once before agents start reading from the server.
        It is idempotent by default; set *force* to ``True`` to overwrite
        existing documents.

        Args:
            force: When ``True``, overwrite existing schema context documents
                with the seed data.  Defaults to ``False``.

        Returns:
            Initialisation result dict from the server (e.g. counts of
            created / skipped records), or ``None`` on failure.
        """
        try:
            return await self.mcp_server.call_tool(
                "initialize_schema_contexts",
                {"force": force},
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.logger.error("Failed to initialize schema contexts: %s", exc)
            return None
