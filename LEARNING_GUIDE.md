# WorkflowBench: Learn It Quickly

This guide is designed for someone who knows basic Python but is still learning APIs and AI agents.

## 90-minute first pass

1. Run the scripted walkthrough. It makes no model call and costs nothing.
2. Read `data/documents.json`, `data/workspace.json` and one case in `data/benchmark.jsonl`.
3. Read `workflowbench/tools.py`: a Sandbox is a disposable copy; write tools require explicit approval.
4. Read `workflowbench/agents.py`: follow the request -> function call -> local tool -> function result -> next request loop.
5. Read `workflowbench/evaluator.py`: graders compare output and actual sandbox state against expected outcomes.
6. Read `workflowbench/experiments.py`: each run starts with a fresh sandbox, is graded and optionally saved.
7. Run `pytest` and explain the project aloud using `docs/INTERVIEW_GUIDE.md`.

## Reading order

`models.py` -> `dataset.py` -> `tools.py` -> `agents.py` -> `evaluator.py` -> `experiments.py` -> `app.py`.

## Key concepts

- **Tool calling:** the model requests a named application function with structured arguments; the application validates and executes it.
- **Orchestration loop:** code that alternates between model requests and tool executions.
- **Execution trace:** chronological record of observable requests, tool results and final output.
- **Deterministic grader:** repeatable rule comparing output/state against explicit expected conditions.
- **Held-out set:** cases kept out of prompt tuning to limit overfitting.
- **Human approval:** a person explicitly permits a consequential operation before the application executes it.

## Live API learning path

The app works in scripted mode without credentials. For a live run, set `OPENAI_API_KEY` in `.env`, use one development case first, and inspect every trace event. Never commit your key.

## Learning honesty

A scripted walkthrough is not a model result. Do not claim improvements until you run matched experiments and inspect the outcomes. This is a local research prototype, not a production agent platform.
