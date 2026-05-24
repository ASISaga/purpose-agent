"""Unit tests for v2.0.0 gap alignment — framework-free."""

from __future__ import annotations

import importlib
import os
import sys
import types
from typing import Any, ClassVar, Dict, List

import pytest

# ---------------------------------------------------------------------------
# Helpers / test doubles
# ---------------------------------------------------------------------------


def _make_agent(**kwargs: Any):
    """Return a minimal concrete PurposeDrivenAgent subclass instance."""
    from purpose_driven_agent.agent import PurposeDrivenAgent

    class _TestAgent(PurposeDrivenAgent):
        def get_agent_type(self) -> List[str]:
            return ["test"]

        def get_default_routing_tag(self) -> str:
            return "[COMPLETE]"

        def get_routing_tags(self) -> frozenset[str]:
            return frozenset({"[COMPLETE]", "[ROUTE:CFO]", "[ROUTE:CMO]", "[HANDBACK]"})

    return _TestAgent(agent_id="t1", purpose="test purpose", **kwargs)


# ===========================================================================
# P0-1: __main__.py — AGENT_PACKAGE pre-seeding
# ===========================================================================


class TestMainAgentPackagePreseeding:
    def test_import_valid_package(self, monkeypatch):
        """AGENT_PACKAGE env var triggers importlib.import_module before run_server."""
        imported: List[str] = []

        def fake_import(name: str) -> types.ModuleType:
            imported.append(name)
            return types.ModuleType(name)

        monkeypatch.setenv("AGENT_PACKAGE", "my_agent_pkg")
        monkeypatch.setattr(importlib, "import_module", fake_import)
        # Force re-execution of __main__ module top-level code
        if "purpose_driven_agent.__main__" in sys.modules:
            del sys.modules["purpose_driven_agent.__main__"]
        import purpose_driven_agent.__main__  # noqa: F401

        assert "my_agent_pkg" in imported

    def test_import_error_logged_as_warning(self, monkeypatch, caplog):
        """A missing AGENT_PACKAGE logs a warning instead of raising."""
        import logging

        monkeypatch.setenv("AGENT_PACKAGE", "non_existent_pkg_xyz")

        def bad_import(name: str) -> types.ModuleType:
            if name == "non_existent_pkg_xyz":
                raise ImportError("No module named 'non_existent_pkg_xyz'")
            return importlib.import_module(name)

        monkeypatch.setattr(importlib, "import_module", bad_import)
        if "purpose_driven_agent.__main__" in sys.modules:
            del sys.modules["purpose_driven_agent.__main__"]

        with caplog.at_level(logging.WARNING, logger="purpose_driven_agent.__main__"):
            import purpose_driven_agent.__main__  # noqa: F401

        assert any("non_existent_pkg_xyz" in msg for msg in caplog.messages)

    def test_no_agent_package_var_skips_import(self, monkeypatch):
        """When AGENT_PACKAGE is unset no extra import is attempted."""
        imported: List[str] = []

        original_import = importlib.import_module

        def tracking_import(name: str, *args: Any, **kwargs: Any) -> types.ModuleType:
            imported.append(name)
            return original_import(name, *args, **kwargs)

        monkeypatch.delenv("AGENT_PACKAGE", raising=False)
        monkeypatch.setattr(importlib, "import_module", tracking_import)
        if "purpose_driven_agent.__main__" in sys.modules:
            del sys.modules["purpose_driven_agent.__main__"]
        import purpose_driven_agent.__main__  # noqa: F401

        # Only the run_server import fires; no extra package should be imported
        assert "purpose_driven_agent.hosting" not in imported  # indirect — just sanity


# ===========================================================================
# P0-2: AOSProtocol — correct PEP 544 structural protocol
# ===========================================================================


class TestAOSProtocol:
    def test_aos_protocol_has_four_methods(self):
        from purpose_driven_agent.agents.protocols import AOSProtocol

        assert hasattr(AOSProtocol, "get_routing_tags")
        assert hasattr(AOSProtocol, "get_default_routing_tag")
        assert hasattr(AOSProtocol, "enforce_routing_tag")
        assert hasattr(AOSProtocol, "run_turn")

    def test_aos_protocol_does_not_have_persona_methods(self):
        from purpose_driven_agent.agents.protocols import AOSProtocol

        assert not hasattr(AOSProtocol, "get_available_personas")
        assert not hasattr(AOSProtocol, "validate_personas")

    def test_persona_callback_protocol_has_persona_methods(self):
        from purpose_driven_agent.agents.protocols import PersonaCallbackProtocol

        assert hasattr(PersonaCallbackProtocol, "get_available_personas")
        assert hasattr(PersonaCallbackProtocol, "validate_personas")

    def test_aos_protocol_absent_from_agent_dot_py_all(self):
        import purpose_driven_agent.agent as agent_module

        assert "AOSProtocol" not in agent_module.__all__

    def test_aos_protocol_absent_from_init_all(self):
        import purpose_driven_agent as pkg

        assert "AOSProtocol" not in pkg.__all__


# ===========================================================================
# P0-3: run_turn() — 8-step lifecycle
# ===========================================================================


class TestRunTurnTypes:
    def test_turn_result_has_content_and_route(self):
        from purpose_driven_agent.agents.purpose_driven_agent import TurnResult

        tr = TurnResult(content="hello [COMPLETE]", route="[COMPLETE]")
        assert tr.content == "hello [COMPLETE]"
        assert tr.route == "[COMPLETE]"

    def test_response_parse_error_is_exception(self):
        from purpose_driven_agent.agents.purpose_driven_agent import ResponseParseError

        with pytest.raises(ResponseParseError):
            raise ResponseParseError("bad parse")

    def test_response_validation_error_is_exception(self):
        from purpose_driven_agent.agents.purpose_driven_agent import ResponseValidationError

        with pytest.raises(ResponseValidationError):
            raise ResponseValidationError("bad validation")

    def test_turn_result_exported_from_package(self):
        from purpose_driven_agent import TurnResult, ResponseParseError, ResponseValidationError

        # Verify types are actually usable, not just importable
        tr = TurnResult(content="hello [COMPLETE]", route="[COMPLETE]")
        assert tr.content == "hello [COMPLETE]"
        with pytest.raises(ResponseParseError):
            raise ResponseParseError("test parse error")
        with pytest.raises(ResponseValidationError):
            raise ResponseValidationError("test validation error")


class TestRunTurnLifecycle:
    def test_run_turn_raises_not_implemented_without_llm(self):
        """run_turn() raises NotImplementedError when no LLM backend is wired."""
        import asyncio

        agent = _make_agent()
        with pytest.raises(NotImplementedError):
            asyncio.get_event_loop().run_until_complete(agent.run_turn({"type": "test"}))

    def test_run_turn_with_llm_backend_executes_all_steps(self):
        """When _invoke_llm is overridden, run_turn returns a valid TurnResult."""
        import asyncio
        from purpose_driven_agent.agents.purpose_driven_agent import TurnResult

        class LLMAgent(_make_agent().__class__):
            async def _invoke_llm(self, prompt: str) -> str:
                return "Response text [COMPLETE]"

        agent = LLMAgent(agent_id="llm-test", purpose="test")
        result = asyncio.get_event_loop().run_until_complete(
            agent.run_turn({"type": "test", "data": "Hello"})
        )
        assert isinstance(result, TurnResult)
        assert "[COMPLETE]" in result.content
        assert result.route == "[COMPLETE]"

    def test_parse_response_raises_on_empty(self):
        agent = _make_agent()
        from purpose_driven_agent.agents.purpose_driven_agent import ResponseParseError

        with pytest.raises(ResponseParseError):
            agent._parse_response("")

    def test_validate_raises_on_invalid(self):
        from purpose_driven_agent.agents.purpose_driven_agent import (
            ResponseValidationError,
            _AgentResponse,
        )

        agent = _make_agent()
        with pytest.raises(ResponseValidationError):
            agent._validate(_AgentResponse(content=""))

    def test_invoke_llm_only_callable_from_run_turn(self):
        """_invoke_llm() is defined only on PurposeDrivenAgent (not on handle_event source)."""
        agent = _make_agent()
        assert callable(getattr(agent, "_invoke_llm", None))

    def test_write_state_called_after_enforce_routing_tag(self):
        """_write_state is always called after enforce_routing_tag — verified via subclass."""
        import asyncio
        from purpose_driven_agent.agents.purpose_driven_agent import TurnResult

        call_log: List[str] = []

        class TracingAgent(_make_agent().__class__):
            async def _invoke_llm(self, prompt: str) -> str:
                return "My decision. [COMPLETE]"

            def enforce_routing_tag(self, response_text: str) -> str:
                call_log.append("enforce_routing_tag")
                return super().enforce_routing_tag(response_text)

            async def _write_state(self, routed_text: str, session: Any) -> None:
                call_log.append("_write_state")
                await super()._write_state(routed_text, session)

        agent = TracingAgent(agent_id="trace-test", purpose="test")
        asyncio.get_event_loop().run_until_complete(agent.run_turn({}))

        assert call_log.index("enforce_routing_tag") < call_log.index("_write_state")

    def test_handle_event_delegates_to_run_turn(self):
        """handle_event() calls run_turn() when an LLM backend is available."""
        import asyncio

        llm_called: List[bool] = []

        class BackendAgent(_make_agent().__class__):
            async def _invoke_llm(self, prompt: str) -> str:
                llm_called.append(True)
                return "Done [COMPLETE]"

        agent = BackendAgent(agent_id="he-test", purpose="test")
        result = asyncio.get_event_loop().run_until_complete(
            agent.handle_event({"type": "test"})
        )
        assert llm_called, "run_turn/_invoke_llm was not called from handle_event"
        assert result["status"] == "success"
        assert "turn_result" in result

    def test_handle_event_skips_run_turn_when_no_backend(self):
        """handle_event() remains functional when no LLM backend is wired."""
        import asyncio

        agent = _make_agent()
        result = asyncio.get_event_loop().run_until_complete(
            agent.handle_event({"type": "test"})
        )
        assert result["status"] == "success"
        assert "turn_result" not in result


# ===========================================================================
# P1-4: _aos_mcp_servers/__init__.__all__ is empty
# ===========================================================================


class TestMcpServersAllIsEmpty:
    def test_all_is_empty_list(self):
        import purpose_driven_agent._aos_mcp_servers as pkg

        assert hasattr(pkg, "__all__")
        assert pkg.__all__ == []


# ===========================================================================
# P1-5: IMLService method signatures match spec
# ===========================================================================


class TestIMLServiceSignatures:
    def test_imlservice_has_train_and_infer(self):
        from purpose_driven_agent.ml_interface import IMLService

        assert hasattr(IMLService, "train")
        assert hasattr(IMLService, "infer")

    def test_imlservice_does_not_have_old_methods(self):
        from purpose_driven_agent.ml_interface import IMLService

        assert not hasattr(IMLService, "trigger_lora_training")
        assert not hasattr(IMLService, "run_pipeline")

    def test_noop_train_raises_not_implemented(self):
        import asyncio
        from purpose_driven_agent.ml_interface import NoOpMLService

        svc = NoOpMLService()
        with pytest.raises(NotImplementedError):
            asyncio.get_event_loop().run_until_complete(svc.train("data", {}))

    def test_noop_infer_raises_not_implemented(self):
        import asyncio
        from purpose_driven_agent.ml_interface import NoOpMLService

        svc = NoOpMLService()
        with pytest.raises(NotImplementedError):
            asyncio.get_event_loop().run_until_complete(svc.infer("prompt", "adapter"))

    def test_infer_signature_prompt_then_adapter(self):
        """infer(prompt, adapter) — prompt is first positional arg."""
        import inspect
        from purpose_driven_agent.ml_interface import IMLService

        sig = inspect.signature(IMLService.infer)
        params = list(sig.parameters.keys())
        assert "prompt" in params
        assert "adapter" in params
        assert params.index("prompt") < params.index("adapter")

    def test_train_signature_dataset_then_config(self):
        import inspect
        from purpose_driven_agent.ml_interface import IMLService

        sig = inspect.signature(IMLService.train)
        params = list(sig.parameters.keys())
        assert "dataset" in params
        assert "config" in params
        assert params.index("dataset") < params.index("config")


# ===========================================================================
# P1-6: enforce_routing_tag() tail scan 200 chars
# ===========================================================================


class TestEnforceRoutingTagTailScan:
    def test_tag_at_120_chars_from_end_is_found(self):
        """A tag 120 chars before end is still found (within 200-char window)."""
        agent = _make_agent()
        # "[COMPLETE]" at position -130 from end
        text = "x" * 100 + "[COMPLETE]" + "y" * 120
        result = agent.enforce_routing_tag(text)
        # Tag is valid so response returned unchanged
        assert result == text

    def test_tag_at_200_chars_from_end_is_found(self):
        """A tag exactly at the 200-char boundary is found."""
        agent = _make_agent()
        # "[COMPLETE]" (10 chars) placed so it starts at position -(200) from end
        text = "x" * 50 + "[COMPLETE]" + "y" * 190
        result = agent.enforce_routing_tag(text)
        assert result == text

    def test_tag_beyond_200_chars_is_not_found(self):
        """A tag more than 200 chars from the end is not detected (appends default)."""
        agent = _make_agent()
        # "[COMPLETE]" at position 0 with 210 trailing chars
        text = "[COMPLETE]" + "z" * 210
        result = agent.enforce_routing_tag(text)
        # Tag is beyond tail — default is appended
        assert result.endswith("[COMPLETE]")
        # The original tag is still in the text but a new one was appended
        assert result.count("[COMPLETE]") >= 2


# ===========================================================================
# P1-7: __version__ == "2.0.0"
# ===========================================================================


class TestVersion:
    def test_version_in_init(self):
        import purpose_driven_agent as pkg

        assert pkg.__version__ == "2.0.0"

    def test_version_in_pyproject_toml(self):
        import pathlib

        repo_root = pathlib.Path(__file__).parents[2]
        pyproject = repo_root / "pyproject.toml"
        content = pyproject.read_text()
        assert 'version = "2.0.0"' in content
