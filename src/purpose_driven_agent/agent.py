"""Backward-compatible exports for agent classes and protocols."""

from purpose_driven_agent.agents import (
    A2AAgentTool,
    GenericPurposeDrivenAgent,
    MCPServerProtocol,
    PersonaCallbackProtocol,
    PurposeDrivenAgent,
    _AGENT_REGISTRY,
)

__all__ = [
    "A2AAgentTool",
    "MCPServerProtocol",
    "PersonaCallbackProtocol",
    "PurposeDrivenAgent",
    "GenericPurposeDrivenAgent",
    "_AGENT_REGISTRY",
]
