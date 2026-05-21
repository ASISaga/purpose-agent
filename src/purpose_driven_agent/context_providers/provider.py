from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from purpose_driven_agent.context_providers.context import Context


class ContextProvider(ABC):
    """Abstract base class for agent context providers.

    A ContextProvider bridges an external data source (MCP server, database,
    conversation history) into the :class:`~purpose_driven_agent.PurposeDrivenAgent`
    reasoning context.

    Implement :meth:`get_context` to fetch and engineer data into a
    :class:`Context` object.  The agent calls this method before each
    reasoning cycle and stores the resulting instructions in its MCP context
    server.

    Example::

        class MyContextProvider(ContextProvider):
            async def get_context(
                self,
                messages: List[Dict[str, Any]],
                **kwargs: Any,
            ) -> Context:
                data = await fetch_my_data()
                return Context(
                    instructions=f"DOMAIN CONTEXT:\\n{data}",
                    messages=messages,
                )
    """

    @abstractmethod
    async def get_context(
        self,
        messages: List[Dict[str, Any]],
        **kwargs: Any,
    ) -> Context:
        """Retrieve and engineer context for injection into the LLM reasoning loop.

        Args:
            messages: Current conversation or event messages.  The provider
                may window or filter these for token efficiency before
                returning them in the :class:`Context`.
            **kwargs: Additional keyword arguments forwarded from the caller.

        Returns:
            :class:`Context` containing engineered instructions and messages.
        """
