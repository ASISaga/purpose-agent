# Changelog

All notable changes to `purpose-driven-agent` are documented here.

## [2.0.0] — 2026-05-24

### Breaking Changes

- **`IMLService` interface redesigned** — `trigger_lora_training(training_params, adapters)` renamed to `train(dataset, config)`; `infer(agent_id, prompt)` signature changed to `infer(prompt, adapter)`; `run_pipeline()` removed. Existing `IMLService` implementations must be updated.
- **`AOSProtocol` redefined** — Now a PEP 544 structural protocol for the agent interaction interface (`get_routing_tags`, `get_default_routing_tag`, `enforce_routing_tag`, `run_turn`). The previous persona callback protocol (`get_available_personas`, `validate_personas`) is extracted to `PersonaCallbackProtocol`.
- **`AOSProtocol` removed from `__all__`** — `agent.py` and `agents/__init__.py` no longer export `AOSProtocol` from `__all__`. Import directly from `purpose_driven_agent.agents.protocols` if needed.
- **`act()` actions updated** — `"trigger_lora_training"` and `"run_azure_ml_pipeline"` actions removed; use `"train"` (with `dataset`, `config` keys) instead.

### New Features

- **`run_turn()` 8-step lifecycle** — Deterministic per-turn execution implementing the LLM-as-English-API contract. Exactly one `_invoke_llm()` call per turn; `_write_state()` always follows `enforce_routing_tag()`.
- **`TurnResult`** — Return type of `run_turn()`; carries `content` (routed response) and `route` (extracted tag).
- **`ResponseParseError`** — Raised by `_parse_response()` when the LLM response cannot be parsed.
- **`ResponseValidationError`** — Raised by `_validate()` when a parsed response fails schema validation.
- **`PersonaCallbackProtocol`** — Structural protocol for objects exposing `get_available_personas()` / `validate_personas()` (extracted from former `AOSProtocol`).
- **`AGENT_PACKAGE` pre-seeding** — `__main__.py` now imports the package named in `AGENT_PACKAGE` env var before `run_server()`, guaranteeing the leaf agent class wins the `_AGENT_REGISTRY` race in multi-layer FAS images.

### Changes

- **`enforce_routing_tag()`** — Response tail scan window widened from 120 → 200 characters.
- **`_aos_mcp_servers/__init__.__all__`** — Set to `[]`; the subpackage remains private and its transport classes are not exported.
- **`__version__`** bumped to `"2.0.0"` in `__init__.py` and `pyproject.toml`.

## [1.0.0] — Initial release
