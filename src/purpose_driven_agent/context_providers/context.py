from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class Context:
    """Structured context object injected into the agent's LLM reasoning loop.

    Returned by :meth:`ContextProvider.get_context` and stored in the agent's
    :class:`~purpose_driven_agent.ContextMCPServer` before each reasoning cycle.

    Attributes:
        instructions: System-level instruction block engineered from remote
            data and injected as high-priority context into the LLM window.
        messages: Conversation messages, possibly windowed or filtered by the
            provider for token efficiency.  Defaults to an empty list.
    """

    instructions: str
    messages: List[Dict[str, Any]] = field(default_factory=list)
