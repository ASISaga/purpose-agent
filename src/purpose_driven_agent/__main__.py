"""
Entry point for running purpose_driven_agent as a FAS hosted container.

Executed by:
    CMD ["python", "-m", "purpose_driven_agent"]

or equivalently:
    python -m purpose_driven_agent
"""
import importlib
import logging
import os

logger = logging.getLogger(__name__)

# ── AGENT_PACKAGE Pre-Seeding ─────────────────────────────────────────────────
# Import the leaf agent package declared in AGENT_PACKAGE before run_server()
# fires.  This guarantees the leaf class is registered in _AGENT_REGISTRY via
# __init_subclass__ *before* _ensure_imports() alphabetical walk, preventing
# intermediate layer classes (e.g. BusinessAgent) from winning the registry
# race when multi-layer images are used.
_agent_package = os.environ.get("AGENT_PACKAGE")
if _agent_package:
    try:
        importlib.import_module(_agent_package)
        logger.debug("AGENT_PACKAGE pre-seeded: %s", _agent_package)
    except ImportError as _exc:
        logger.warning("AGENT_PACKAGE '%s' could not be imported: %s", _agent_package, _exc)

from purpose_driven_agent.hosting import run_server  # noqa: E402

if __name__ == "__main__":
    run_server()
