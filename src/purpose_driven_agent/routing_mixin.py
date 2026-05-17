"""
RoutingMixin — declares an agent's role in the routing protocol.

Usage:
    class FounderAgent(RoutingMixin, BusinessAgent):
        ROUTING_ROLE = "orchestrator"
        # get_default_routing_tag() returns "[COMPLETE]"

    class CFOAgent(RoutingMixin, BusinessAgent):
        ROUTING_ROLE = "specialist"
        # get_default_routing_tag() returns "[HANDBACK]"
"""
from __future__ import annotations

from typing import ClassVar, Literal

_ORCHESTRATOR_TAGS = frozenset({"[ROUTE:CFO]", "[ROUTE:CMO]", "[COMPLETE]"})
_SPECIALIST_TAGS = frozenset({"[HANDBACK]"})


class RoutingMixin:
    """
    Mixin that configures the routing tag enforcement in PurposeDrivenAgent.

    Must be mixed in before PurposeDrivenAgent in the MRO:
        class FounderAgent(RoutingMixin, BusinessAgent): ...
    where BusinessAgent inherits from PurposeDrivenAgent.

    Attributes:
        ROUTING_ROLE: "orchestrator" or "specialist".
            orchestrators emit [ROUTE:CFO], [ROUTE:CMO], or [COMPLETE]
            specialists emit [HANDBACK]
    """

    ROUTING_ROLE: ClassVar[Literal["orchestrator", "specialist"]] = "orchestrator"

    def get_routing_tags(self) -> frozenset[str]:
        if self.ROUTING_ROLE == "specialist":
            return _SPECIALIST_TAGS
        return _ORCHESTRATOR_TAGS

    def get_default_routing_tag(self) -> str:
        if self.ROUTING_ROLE == "specialist":
            return "[HANDBACK]"
        return "[COMPLETE]"
