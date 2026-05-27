"""
IMLService - Abstract ML service interface for LoRA training and inference.

PurposeDrivenAgent uses this interface for all ML pipeline operations so that
the core agent logic remains decoupled from a specific ML backend (Azure ML,
local, mock, etc.).

Implement :class:`IMLService` and pass it to the agent's ``act()`` method or
configure it via the ``config`` dict under the ``"ml_service"`` key to plug in
your own training / inference backend.

Example - mock service for tests::

    from purpose_driven_agent.ml_interface import IMLService

    class MockMLService(IMLService):
        async def train(self, dataset, config):
            return "training-run-mock-001"

        async def infer(self, prompt, adapter):
            return {"text": f"Mock response for {adapter}: {prompt}"}

Example - Azure ML backend::

    from purpose_driven_agent.ml_interface import IMLService
    from azure_ml_lora import LoRATrainer, UnifiedMLManager

    class AzureMLService(IMLService):
        async def train(self, dataset, config):
            trainer = LoRATrainer(
                model_name=config["model_name"],
                data_path=dataset,
                output_dir=config["output_dir"],
                adapters=config.get("adapters", []),
            )
            trainer.train()
            return f"Training complete, adapters saved to {config['output_dir']}"

        async def infer(self, prompt, adapter):
            mgr = UnifiedMLManager(...)
            return await mgr.infer(adapter, prompt)
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class IMLService(ABC):
    """
    Abstract interface for ML pipeline operations used by PurposeDrivenAgent.

    Implementors supply the actual compute backend (Azure ML, local, mock…).
    The default no-op implementation raises :class:`NotImplementedError` for
    all methods, making missing implementations obvious at call time.
    """

    @abstractmethod
    async def train(
        self,
        dataset: Any,
        config: Dict[str, Any],
    ) -> Any:
        """
        Fine-tune a LoRA adapter from *dataset* using *config*.

        Args:
            dataset: Training dataset (path, object, or identifier — format
                is backend-specific).
            config: Training configuration dict.  Recognised keys depend on
                the backend; at minimum:

                - ``model_name`` (str): base model identifier.
                - ``output_dir`` (str): where to write the trained adapter.

        Returns:
            Adapter artefact (identifier string, path, or backend-specific
            object) suitable for passing to :meth:`infer`.
        """

    @abstractmethod
    async def infer(self, prompt: str, adapter: Any) -> Any:
        """
        Run inference with *adapter* applied to the base model.

        Args:
            prompt: Input prompt string.
            adapter: LoRA adapter artefact returned by :meth:`train`, or an
                adapter name/identifier recognised by the backend.

        Returns:
            Raw LLM response (typically a ``str`` or ``{"text": str}`` dict).
        """


class NoOpMLService(IMLService):
    """
    No-operation implementation of :class:`IMLService`.

    Raises :class:`NotImplementedError` for every method, which surfaces
    clearly when ML operations are attempted without a real backend.
    Useful as a placeholder when an agent does not require ML operations.
    """

    async def train(self, dataset: Any, config: Dict[str, Any]) -> Any:
        raise NotImplementedError(
            "ML backend not configured. Provide an IMLService implementation."
        )

    async def infer(self, prompt: str, adapter: Any) -> Any:
        raise NotImplementedError(
            "ML backend not configured. Provide an IMLService implementation."
        )
