"""Backward-compatible exports for agent classes and protocols."""

from purpose_driven_agent.agents import (
    A2AAgentTool,
    AOSProtocol,
    GenericPurposeDrivenAgent,
    MCPServerProtocol,
    PurposeDrivenAgent,
    _AGENT_REGISTRY,
)

__all__ = [
    "A2AAgentTool",
    "AOSProtocol",
    "MCPServerProtocol",
    "PurposeDrivenAgent",
    "GenericPurposeDrivenAgent",
    "_AGENT_REGISTRY",
]
