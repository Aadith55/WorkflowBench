# Architecture

## Design goals
- One readable tool-calling loop shared by two agents.
- Fixed local tool registry with strict argument validation.
- Disposable in-memory sandbox for all example state changes.
- Deterministic grading wherever possible.
- Local SQLite history; no external system writes.

## Request path
1. Streamlit or CLI selects a benchmark case and strategy.
2. `experiments.run_one_case` creates a fresh `Sandbox`.
3. `agents.run_live_agent` sends task, instructions and strict function schemas to the Responses API.
4. Function calls are passed to `Sandbox.call`.
5. Pydantic validates arguments and the sandbox checks agent permissions and write approval.
6. Tool output is returned to the model; trace events and usage are recorded.
7. `evaluator.evaluate_run` grades answer and/or final sandbox state.
8. Metrics and run trace are saved to SQLite.

## Main modules
- `dataset.py`: JSONL loading and basic integrity checks.
- `models.py`: AgentRun and TraceEvent data structures.
- `tools.py`: schemas, argument models, sandbox and local tool implementations.
- `agents.py`: shared model/tool orchestration loop.
- `evaluator.py`: task-specific deterministic graders.
- `analytics.py`: Wilson interval, summaries and paired exact McNemar calculation.
- `storage.py`: local experiment history.
- `app.py`: Streamlit interface.
- `cli.py`: scripted walkthroughs and small live batches.

## Security boundaries
- Agents see only their own tool subset.
- Writes require explicit approval.
- All writes remain in a fresh in-memory sandbox and disappear after the run.
- Message drafts are not sent.
- No deletion tool exists.
- Incident closure is blocked until recovery validation exists in the record.
- Retrieved documents are treated as data, never instructions.

## Deliberate limitations
This version has no authentication, multi-user server, production integrations, embeddings, distributed queue or durable business writes. Keyword retrieval is a simple baseline, not a production search system.


## Experiment comparability

Each run stores the model ID, benchmark version and write-approval setting alongside its metrics. The dashboard only pairs baseline and verified results when these settings match. This is important because workflow tasks with write tools enabled are not directly comparable to runs where writes are disabled.
