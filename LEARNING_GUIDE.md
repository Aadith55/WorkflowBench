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

`models.py` -> `dataset.py` -> `tools.py` -> `agents.py` / `gemini_agent.py` / `ollama_agent.py` -> `evaluator.py` -> `experiments.py` -> `app.py`.

## Key concepts

- **Tool calling:** the model requests a named application function with structured arguments; the application validates and executes it.
- **Orchestration loop:** code that alternates between model requests and tool executions.
- **Execution trace:** chronological record of observable requests, tool results and final output.
- **Deterministic grader:** repeatable rule comparing output/state against explicit expected conditions.
- **Held-out set:** cases kept out of prompt tuning to limit overfitting.
- **Human approval:** a person explicitly permits a consequential operation before the application executes it.

## Live model learning path (no API billing)

Use Ollama for the first real model run. It runs on your computer and does not need an API key or hosted inference credits.

1. Install [Ollama for Windows](https://ollama.com/download/windows).
2. Check available RAM before selecting the model. WorkflowBench is configured with `qwen3:4b` as its starter model.
3. In PowerShell, run `ollama pull qwen3:4b`, then `ollama list` to confirm it is installed.
4. Keep Ollama running and start the dashboard with `streamlit run app.py`.
5. Select **Live model run** and **Ollama (local, no API key)**. Start with one development case and inspect the complete trace.

You can also run one case from the terminal:

```powershell
python -m workflowbench.cli benchmark --provider ollama --agent knowledge --strategy baseline --split development --limit 1
```

Then run a small matched pilot:

```powershell
python -m workflowbench.cli compare --provider ollama --agent both --split development --cases-per-agent 2 --repetitions 1
```

The Gemini adapter is optional and depends on project free-tier eligibility and quota. OpenAI API calls may require paid credits, so they are not part of the no-cost path. Never commit API keys.

## Learning honesty

A scripted walkthrough is not a model result. Do not claim improvements until you run matched experiments and inspect the outcomes. This is a local research prototype, not a production agent platform.


## Understanding the experiment history

A saved live run includes its model ID, benchmark version and whether workflow writes were enabled. This is not just bookkeeping. When comparing baseline with verified instructions, the model and permissions must be the same. The dashboard groups results by those settings and only runs a paired comparison when the configurations match.

The scripted walkthrough is a fixed example (K01 or W01). It teaches the tool flow, but it does not execute the selected benchmark case and it does not call a model.
