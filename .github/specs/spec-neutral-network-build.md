# Neutral Network Build Specification

**v2.0.0 | ACR Bytecode Layer Contract**

---

## Identity

Build contract for `aos/purpose-driven-agent` — the `.pyc`-only ACR image layer. Defines compilation, packaging, verification, and propagation of the Layer 2 neutral network neuron. Shared build infrastructure owned by `ASISaga/aos-infra`.

Whitepaper: `boardroom-whitepaper-v4.md` §3.4 — The Neutral Network Build, §5 — Layer 4: GitHub Pipelines

---

## Build Artefact Contract

| Property | Value |
|---|---|
| ACR image | `acraosstagingerm2srfd.azurecr.io/aos/purpose-driven-agent` |
| Parent image | `aos/infra` — Layer 0 external dependencies |
| Artefact | `.pyc` only — `compileall -b -j0 -q`, `.py` deleted before ACR push |
| `PYTHONPATH` | `/app:/app/lib/python3.12/site-packages` — `ENV` in `Dockerfile.aos-agent` |
| `CMD` | `python -m purpose_driven_agent` — shell form |
| Dockerfile | `Dockerfile.aos-agent` — owned by `ASISaga/aos-infra`, not modified here |

---

## Compilation Contract

GitHub Actions runner compiles `.py` → `.pyc`. Build context sent to ACR Task contains `.pyc` only.

```
cp -r src/purpose_driven_agent/. compiled/purpose_driven_agent/
python -m compileall -b -j0 -q compiled/purpose_driven_agent/
find compiled/ -name "*.py" -delete
```

`-b` flag: writes `.pyc` beside source (not in `__pycache__/`) — required for `SourcelessFileLoader` at runtime. Verification: `find /app/${PACKAGE_DIR}/ -name "*.pyc"` — build fails if empty.

---

## Propagation Contract

| Trigger | Mechanism | Effect |
|---|---|---|
| Push to `main` (source change) | `az acr build` → ACR Task | New `.pyc` layer pushed to `aos/purpose-driven-agent:latest` |
| Non-breaking parent bump | `crane rebase` | Manifest pointer updated — zero bytes of bytecode transferred |
| Post-build | `manifest-update` dispatch | `ASISaga/leadership-agent` receives `repository_dispatch` event |

---

## Verification Steps

| Step | Verification |
|---|---|
| Compile | `0 .py` files remain in `compiled/` |
| Compile | `N > 0 .pyc` files present in `compiled/` |
| ACR Task | `find /app/${PACKAGE_DIR}/ -name "*.pyc"` non-empty |
| Link test | `az container exec` — full import chain resolves from `.pyc` |
| Link test | `get_hosted_agent()` returns correct leaf class |
| Link test | `get_routing_tags()` and `get_default_routing_tag()` correct |

---

## Invariants

- `Dockerfile.aos-agent` owned by `ASISaga/aos-infra` — never modified in this repo
- `.py` source never enters the ACR image
- `PYTHONPATH` baked into image — not set at container runtime
- `CMD` is shell form — not JSON array — enabling variable expansion
- Build context is always `compiled/` directory contents — not full repo

---

## Related Specifications

| Concern | Specification |
|---|---|
| FAS hosting | `.github/specs/fas-hosting.md` |
| Repository ownership | `.github/specs/repository.md` |
