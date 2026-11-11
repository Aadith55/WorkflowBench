# WorkflowBench v0.1 Status

## Implemented
- Two agent types with a shared Responses API function-calling loop.
- Strict tool schemas and local Pydantic argument validation.
- Disposable in-memory document/workspace sandbox.
- Write approval gate, no-send drafts, no-delete surface and incident closure precondition.
- 24 synthetic benchmark cases (12 per agent; 8 development and 16 held out).
- Deterministic graders and baseline/verified instructions.
- Trace, token and latency capture; local SQLite history.
- Streamlit dashboard, CLI, scripted walkthrough and statistical helpers.
- Learning, architecture, evaluation and research documentation.

## Not yet established
- Live API execution must be run with a user-provided API key.
- No model-performance improvement, cost saving or market opportunity has been measured.
- Competitive landscape research and human review of cases remain future work.
- The starter benchmark is exploratory and is not representative of real customer traffic.
