# WorkflowBench

**A research prototype for AI workflow orchestration, evaluation and operational trade-offs.**

WorkflowBench studies whether an AI agent completes a task correctly, uses tools appropriately, respects safety boundaries and produces measurable value. It contains two agent types that share one execution loop:

1. **Knowledge & Research Agent** — searches a small document library, retrieves source documents and answers with citations.
2. **Workflow Execution Agent** — reads structured workspace records and can create tasks, update record status or save message drafts inside a disposable local sandbox.

The first version is deliberately small and teachable. It avoids agent frameworks, vector databases, queues, external connectors and production deployment complexity.

## Important scope notes

- The benchmark contains **24 original starter scenarios**: 12 knowledge tasks and 12 workflow tasks.
- Eight scenarios are marked `development`; 16 are marked `evaluation`.
- Results from this small benchmark are exploratory. Do not describe them as statistically conclusive or generalised to production agents.
- Live runs can use the OpenAI Responses API or Google's Gemini API through its OpenAI-compatible Chat Completions endpoint.
- A fully offline **local simulation** runs all benchmark cases through the sandbox and deterministic grader without an LLM, network request or API key. It is a pipeline rehearsal, not model evaluation.
- The local simulation is fixture-driven: it reads benchmark expected labels to stage known tool sequences. Its pass rate must not be presented as LLM performance.
- The scripted walkthrough is a fixed teaching example. It is **not** an LLM run and its output must not be used as model performance evidence.
- Function-call arguments are checked locally with Pydantic before a tool runs. The model-facing strict JSON Schemas use the supported Structured Outputs subset; stricter length and calendar-date checks remain in the application.
- All example data is synthetic. All writes happen in memory and are discarded after a run. `draft_message` never sends a message. There is no delete tool.
- Cost is calculated only when you enter verified token prices in `.env`; otherwise token counts are recorded and cost remains unknown.

## 1. Quick start

Python 3.11 or newer is recommended.

### Windows PowerShell

```powershell
cd WorkflowBench
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
Copy-Item .env.example .env
streamlit run app.py
```

### macOS / Linux

```bash
cd WorkflowBench
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
cp .env.example .env
streamlit run app.py
```

Open the local Streamlit URL printed in the terminal.

Start with **Scripted walkthrough** to see a fixed teaching example, or choose **Local simulation (no LLM)** to run a benchmark case through the local sandbox. Neither mode needs an API key.

For a complete offline pipeline rehearsal, run:

```bash
python -m workflowbench.cli simulate --agent both --split all
```

This runs all 24 labelled scenarios and writes:
- `simulation_summary.json`
- `simulation_results.csv`
- `simulation_traces.json`

These are fixture-driven pipeline checks, not model results. The simulation intentionally does not write to the normal live-run SQLite history.

## 2. Run a real model with Gemini's free tier

Google AI Studio currently offers a limited free tier for selected Gemini API models. India is in the supported-region list. Free-tier quotas are limited and can change; Google states that free-tier content may be used to improve its products. WorkflowBench uses synthetic example data, but do not send private or sensitive information.

1. Open [Google AI Studio API Keys](https://aistudio.google.com/app/apikey).
2. Create an API key. Do not set up paid billing.
3. Copy `.env.example` to `.env` and set `GEMINI_API_KEY`.
4. Keep `GEMINI_MODEL=gemini-3.8-flash` initially.
5. Restart Streamlit, select **Live model run**, choose **Gemini API (free tier)**, and select a single benchmark case.
6. For workflow tasks, enable **Allow writes to the disposable local sandbox**. The app never connects to real systems or sends messages.

Never commit `.env` or paste an API key into source code. The `.gitignore` excludes it.

To run an actual matched baseline-versus-verified pilot on the Gemini free tier:

```bash
python -m workflowbench.cli compare --provider gemini --agent both --split development --cases-per-agent 2 --repetitions 1
```

This makes eight real model runs (four scenarios under two strategies) and saves a summary, CSV and traces under `artifacts/live-experiment/`. API quotas can still reject calls with a rate-limit response. Inspect current limits and usage in AI Studio before increasing the run size.

## 3. Run OpenAI live experiments through GitHub Actions

The GitHub Actions workflow currently targets the OpenAI Responses API. Add `OPENAI_API_KEY` as a repository Actions secret, then open **Actions -> Live API experiment -> Run workflow**. The default pilot runs two development cases per agent under both baseline and verified strategies (eight model runs total). Results are uploaded as an artifact containing a summary, CSV metrics and full execution traces.

The Gemini free-tier matched pilot is available through the local CLI command above; it does not require an OpenAI secret or paid OpenAI credits.

See [docs/LIVE_EXPERIMENTS.md](docs/LIVE_EXPERIMENTS.md) for the OpenAI Actions workflow. Never put an API key in source code or a chat message.

## 4. Run tests

```bash
pytest
```

Tests cover dataset loading, sandbox tool boundaries, deterministic grading, statistical helpers, the Responses API loop and the Gemini Chat Completions loop using fake clients. Tests do not make paid API calls.

## 5. Command line

List cases:

```bash
python -m workflowbench.cli list
```

Run a fixed teaching walkthrough:

```bash
python -m workflowbench.cli demo --agent knowledge
python -m workflowbench.cli demo --agent workflow
```

Run a small live batch (API key required):

```bash
python -m workflowbench.cli benchmark --agent knowledge --strategy baseline --split development --limit 2
```

Workflow benchmark tasks require local writes to be enabled:

```bash
python -m workflowbench.cli benchmark --agent workflow --strategy verified --split development --limit 2 --allow-writes
```

Start with small batches. Each live case makes one or more model requests and may incur API cost.

## 6. Project map

```text
WorkflowBench/
├── app.py                         # Small Streamlit research dashboard
├── workflowbench/
│   ├── agents.py                  # OpenAI Responses API tool-calling loop
│   ├── gemini_agent.py            # Gemini Chat Completions tool-calling loop
│   ├── simulation.py              # Offline fixture-driven pipeline rehearsal
│   ├── analytics.py               # Wilson interval and paired McNemar test
│   ├── dataset.py                 # JSONL benchmark loader
│   ├── demo.py                    # Scripted walkthroughs (not model runs)
│   ├── evaluator.py               # Deterministic task graders
│   ├── experiments.py             # Fresh sandbox -> run -> grade -> save
│   ├── models.py                  # Run and trace data structures
│   ├── storage.py                 # SQLite run history
│   └── tools.py                   # Local read/write tools and sandbox
├── data/
│   ├── benchmark.jsonl            # 24 labelled benchmark scenarios
│   ├── documents.json             # Synthetic knowledge base
│   └── workspace.json             # Synthetic business workspace
├── docs/
│   ├── ARCHITECTURE.md
│   ├── EVALUATION_PLAN.md
│   ├── RESEARCH_NOTES.md
│   └── INTERVIEW_GUIDE.md
├── tests/
├── scripts/ (live experiment entry point is a package module)
├── docs/LIVE_EXPERIMENTS.md
├── LEARNING_GUIDE.md
├── .env.example
└── pyproject.toml
```

## 7. The two strategies

- **Baseline:** task-focused instructions and the same approved tool registry.
- **Verified:** adds explicit source retrieval and post-action verification instructions.

Keep the model, dataset version, tool schemas and other settings fixed when comparing strategies. The starter app stores the strategy label, model token usage, timing, trace and deterministic metrics.

## 8. Evaluation approach

Knowledge tasks use deterministic checks for required terms, source retrieval, citation coverage and abstention. Workflow tasks use tool-call coverage and postcondition checks against the sandbox state. We intentionally do not use an LLM to grade another LLM in v0.1.

The dashboard reports task success, tool precision/recall/F1, state-match rate or knowledge-specific metrics, latency and token usage. The exact McNemar helper compares matched case IDs across baseline and verified strategies. Confidence intervals and significance tests must be interpreted cautiously with this small starter set.

See [`docs/EVALUATION_PLAN.md`](docs/EVALUATION_PLAN.md) before running experiments. For free local and Gemini runs, see [`docs/FREE_LOCAL_AND_GEMINI_RUNS.md`](docs/FREE_LOCAL_AND_GEMINI_RUNS.md).

## 9. Research references

- [OpenAI function calling guide](https://developers.openai.com/api/docs/guides/function-calling)
- [OpenAI structured outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs)
- [OpenAI agent evaluation guide](https://developers.openai.com/api/docs/guides/agent-evals)
- [Berkeley Function Calling Leaderboard](https://gorilla.cs.berkeley.edu/leaderboard.html)
- [AgentBench paper](https://arxiv.org/abs/2308.03688)

These are methodological references. WorkflowBench's 24 scenarios are original synthetic examples, not reproductions of these benchmarks.

## 10. Current limitations

- The dataset is small and partly synthetic; it does not represent real customer behaviour.
- Search uses simple keyword matching, not embeddings or a production retrieval system.
- The evaluator is intentionally deterministic and narrow. It does not judge nuanced writing quality.
- The prototype stores experiment history locally in SQLite and has no authentication or multi-user support.
- The baseline/verified comparison is an early prompt-and-verification experiment, not a complete factorial design.
- The GitHub Actions live workflow uses the OpenAI Responses API and requires an OpenAI API key with available quota/billing.
- Gemini API access can use Google's free tier for eligible models, but quotas and data-use terms apply; verify them in AI Studio.
- Token cost is unknown unless verified provider prices are configured.

The next research iteration should add more human-reviewed cases, measure grader agreement, repeat runs for stochasticity, and document failure categories before making performance claims.


### Reproducible experiment settings

Each live run records its model ID, benchmark version and write-approval setting. The dashboard groups task-success rates by these settings and only pairs baseline/verified runs with matching configurations. This prevents comparisons between runs that used different models, dataset versions or workflow write permissions.
