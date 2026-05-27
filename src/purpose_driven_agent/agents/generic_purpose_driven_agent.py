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

    def get_default_routing_tag(self) -> str:
        """
        Return ``"[COMPLETE]"`` as the default routing tag.

        The generic agent acts as an orchestrator — it signals completion
        rather than handing back to a specialist.

        Returns:
            ``"[COMPLETE]"``
        """
        return "[COMPLETE]"

    async def _invoke_llm(self, prompt: str) -> str:
        """
        Concrete LLM invocation for the generic agent.

        Returns a minimal stub response so that :meth:`run_turn` completes
        without raising :class:`NotImplementedError`.  Override this method
        (or wire an ``agent_framework`` backend) to connect a real LLM.

        Args:
            prompt: The assembled prompt from :meth:`_build_prompt`.

        Returns:
            A stub response string that satisfies
            :meth:`_parse_response` and :meth:`_validate`.
        """
        self.logger.debug(
            "GenericPurposeDrivenAgent._invoke_llm: no LLM backend wired — "
            "returning stub response (override to connect a real LLM)."
        )
        return f"[generic-stub] Received prompt ({len(prompt)} chars). No LLM backend wired."
