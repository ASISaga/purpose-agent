"""Backward-compatible exports for context provider classes and factories."""

from purpose_driven_agent.context_providers import (
    SUBCONSCIOUS_MCP_URL,
    Context,
    ContextProvider,
    SubconsciousContextProvider,
    SubconsciousSchemaContextProvider,
    create_subconscious_provider,
    create_subconscious_schema_provider,
)

__all__ = [
    "Context",
    "ContextProvider",
    "SubconsciousContextProvider",
    "SubconsciousSchemaContextProvider",
    "create_subconscious_provider",
    "create_subconscious_schema_provider",
    "SUBCONSCIOUS_MCP_URL",
]
