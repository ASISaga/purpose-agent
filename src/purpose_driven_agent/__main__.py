"""
Entry point for running purpose_driven_agent as a FAS hosted container.

Executed by:
    CMD ["python", "-m", "purpose_driven_agent"]

or equivalently:
    python -m purpose_driven_agent
"""
from purpose_driven_agent.hosting import run_server

if __name__ == "__main__":
    run_server()
