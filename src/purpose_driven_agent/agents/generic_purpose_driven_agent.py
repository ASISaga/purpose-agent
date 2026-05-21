from __future__ import annotations

from typing import List

from purpose_driven_agent.agents.purpose_driven_agent import PurposeDrivenAgent


class GenericPurposeDrivenAgent(PurposeDrivenAgent):
    """
    Concrete general-purpose implementation of :class:`PurposeDrivenAgent`.

    Use this when you need a basic purpose-driven agent without specialised
    functionality.  For domain-specific use cases prefer purpose-built
    subclasses such as ``LeadershipAgent`` or ``CMOAgent``.

    Example::

        from purpose_driven_agent import GenericPurposeDrivenAgent

        agent = GenericPurposeDrivenAgent(
            agent_id="assistant",
            purpose="General assistance and task execution",
            adapter_name="general",
        )
        await agent.initialize()
        await agent.start()
    """

    def get_agent_type(self) -> List[str]:
        """
        Return ``["generic"]``, selecting the generic LoRA adapter persona.

        Queries the AOS registry and falls back to ``["generic"]`` if the
        persona is unavailable.

        Returns:
            ``["generic"]``
        """
        available = self.get_available_personas()
        if "generic" not in available:
            self.logger.warning(
                "'generic' persona not in AOS registry, using default"
            )
        return ["generic"]
