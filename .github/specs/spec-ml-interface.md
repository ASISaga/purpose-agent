# ML Interface Specification

**v2.0.0 | IMLService | LoRA Adapter Boundary**

---

## Identity

The ML interface is the boundary through which AOS drives per-avatar LoRA fine-tuning and adapted inference. Defined in `purpose_driven_agent.ml_interface`. `PurposeDrivenAgent` holds a reference to an `IMLService` instance — AOS owns the fine-tuning pipeline and wires the concrete adapter. This repo defines the contract; AOS implements it.

Whitepaper: `boardroom-whitepaper-v4.md` §5.1 — Layer 1: Voice and Judgment (LoRA Adapters), §5.2 — The Dataset Pipeline

---

## Interface Contract

### `IMLService`

Abstract interface. Two concerns: training and inference.

| Method | Contract |
|---|---|
| `train(dataset, config)` | Fine-tunes a LoRA adapter from `dataset` using `config`; returns adapter artefact |
| `infer(prompt, adapter)` | Runs inference with `adapter` applied to base model; returns raw LLM response |

AOS owns both implementations. `PurposeDrivenAgent` calls `infer()` inside `_invoke_llm()` when an adapter is wired. Training is triggered by AOS pipeline, not by agent code.

### `NoOpMLService`

Default implementation. Raises `NotImplementedError` on both `train()` and `infer()`. Active until AOS wires a concrete `IMLService`. `_invoke_llm()` falls back to base model inference when `NoOpMLService` is active.

---

## LoRA Adapter Architecture

Each avatar has a dedicated LoRA adapter trained on curated persona datasets:

| Avatar | Adapter | Dataset | Training config |
|---|---|---|---|
| Founder | `founder-lora` | PG essays, YC advice, startup writing | `r=16`, attention projections |
| CFO | `cfo-lora` | Buffett letters, annual reports, shareholder memos | `r=16`, attention projections |
| CMO | `cmo-lora` | Godin (0.6) + Erhard (0.4) — TIES merge, density 0.5 | `r=16`, attention projections |

TIES merge for CMO: `cmo-lora = TIES(godin-lora × 0.6, erhard-lora × 0.4, density=0.5)`. Preserves Godin's marketing sensibility and Erhard's ontological grounding in a single adapter.

---

## Dataset Pipeline

Two-stage pipeline owned by AOS. Produces training datasets for each avatar:

| Stage | Mechanism | Role |
|---|---|---|
| Generation | Llama model | Produces candidate training examples in persona voice |
| Audit | Opus 4 | Validates each example against five criteria — routing compliance, register economy, voice coherence, factual grounding, ontological alignment |

Training examples passing audit are compiled into `{avatar}-dataset`. `100%` routing tag presence required across all audited examples.

---

## Adapter Injection Point

LoRA adapter injection occurs at the MAF layer — applied to the base model before `_invoke_llm()` receives the response. `PurposeDrivenAgent` is provider-agnostic: it calls `IMLService.infer()` and receives the adapted response. The adapter is invisible to the routing and validation logic that follows.

---

## Invariants

- `IMLService` is the only ML boundary — no direct model calls in agent code
- `NoOpMLService` is the default — base model inference until AOS wires adapter
- LoRA training is owned entirely by AOS — not triggered by agent code
- Adapter is applied at the MAF layer — not at the `PurposeDrivenAgent` layer
- `train()` and `infer()` are the complete interface — no additional methods

---

## Related Specifications

| Concern | Specification |
|---|---|
| LLM as English API | `.github/specs/llm-api.md` |
| Agent lifecycle | `.github/specs/agent-lifecycle.md` |
| Repository ownership | `.github/specs/repository.md` |
