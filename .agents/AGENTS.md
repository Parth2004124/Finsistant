
# Core Architecture Constraint

The core Finsistant technical orchestrator and primary analysis engine is locked. Any new AI engines, analysis modules, or features MUST be built as independent, self-contained microservices (similar to karlos_simulator.py) that run asynchronously and do not block or modify the core orchestrator's execution flow.
