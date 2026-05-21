from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class A2AAgentTool:
    """Represents a PurposeDrivenAgent as an Agent-to-Agent (A2A) tool.

    This is the data structure returned by :meth:`PurposeDrivenAgent.as_tool`.
    It mirrors the ``azure.ai.projects.models.AgentTool`` shape so that the
    AOS kernel or a coordinator agent can register specialist agents as callable
    tools in the Foundry Agent Service.

    Attributes:
        name: Tool name — the agent's role (e.g. ``"CTO"``).
        description: Tool description — pulled from the agent's purpose
            (mission statement) to guide the LLM's routing logic.
        connection_id: The A2A connection string for the Azure AI Project.
        agent_id: The local agent identifier.
        foundry_agent_id: The Foundry-assigned agent ID (set after registration).
        metadata: Additional metadata about the agent tool.
    """

    name: str
    description: str
    connection_id: str
    agent_id: str
    foundry_agent_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_foundry_tool_definition(self, thread_id: Optional[str] = None) -> Dict[str, Any]:
        """Return a Foundry-compatible tool definition dict.

        This can be passed to ``AIProjectClient.create_agent(tools=[...])``
        to register this agent as a callable tool.

        Args:
            thread_id: Optional thread ID to inject so
                the specialist agent inherits the orchestration context.

        Returns:
            Dictionary compatible with the Foundry Agent Service tool schema.
        """
        definition: Dict[str, Any] = {
            "type": "agent",
            "agent": {
                "name": self.name,
                "description": self.description,
                "connection_id": self.connection_id,
                "agent_id": self.agent_id,
            },
        }
        if self.foundry_agent_id:
            definition["agent"]["foundry_agent_id"] = self.foundry_agent_id
        if thread_id:
            definition["agent"]["thread_id"] = thread_id
        if self.metadata:
            definition["agent"]["metadata"] = self.metadata
        return definition
