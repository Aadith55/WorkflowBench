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
- Live runs use the OpenAI Responses API with strict function schemas. The API key is optional until you choose **Live model run**.
- The scripted walkthrough is a fixed teaching example. It is **not** an LLM run and its output must not be used as model performance evidence.
- Function-call arguments are checked locally with Pydantic before a tool runs.
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

Open the local Streamlit URL printed in the terminal. Start with **Scripted walkthrough**. It does not require an API key.

## 2. Enable a live model run

1. Open `.env`.
2. Add your API key to `OPENAI_API_KEY`.
3. Set `OPENAI_MODEL` to a model available to your API account.
4. Restart Streamlit.
5. Select **Live model run** and choose a single benchmark case.
6. For workflow tasks, explicitly enable **Allow writes to the disposable local sandbox**. Without this approval, write tools are blocked.

Never commit `.env` or paste an API key into source code. The `.gitignore` excludes it.

## 3. Run tests

```bash
pytest
```

Tests cover dataset loading, sandbox tool boundaries, deterministic grading, statistical helpers and the Responses API tool loop using a fake client. Tests do not make paid API calls.

## 4. Command line

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

## 5. Project map

```text
WorkflowBench/
├── app.py                         # Small Streamlit research dashboard
├── workflowbench/
│   ├── agents.py                  # One readable Responses API tool-calling loop
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
├── LEARNING_GUIDE.md
├── .env.example
└── pyproject.toml
```

## 6. The two strategies

- **Baseline:** task-focused instructions and the same approved tool registry.
- **Verified:** adds explicit source retrieval and post-action verification instructions.

Keep the model, dataset version, tool schemas and other settings fixed when comparing strategies. The starter app stores the strategy label, model token usage, timing, trace and deterministic metrics.

## 7. Evaluation approach

Knowledge tasks use deterministic checks for required terms, source retrieval, citation coverage and abstention. Workflow tasks use tool-call coverage and postcondition checks against the sandbox state. We intentionally do not use an LLM to grade another LLM in v0.1.

The dashboard reports task success, tool precision/recall/F1, state-match rate or knowledge-specific metrics, latency and token usage. The exact McNemar helper compares matched case IDs across baseline and verified strategies. Confidence intervals and significance tests must be interpreted cautiously with this small starter set.

See [`docs/EVALUATION_PLAN.md`](docs/EVALUATION_PLAN.md) before running experiments.

## 8. Research references

- [OpenAI function calling guide](https://developers.openai.com/api/docs/guides/function-calling)
- [OpenAI structured outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs)
- [OpenAI agent evaluation guide](https://developers.openai.com/api/docs/guides/agent-evals)
- [Berkeley Function Calling Leaderboard](https://gorilla.cs.berkeley.edu/leaderboard.html)
- [AgentBench paper](https://arxiv.org/abs/2308.03688)

These are methodological references. WorkflowBench's 24 scenarios are original synthetic examples, not reproductions of these benchmarks.

## 9. Current limitations

- The dataset is small and partly synthetic; it does not represent real customer behaviour.
- Search uses simple keyword matching, not embeddings or a production retrieval system.
- The evaluator is intentionally deterministic and narrow. It does not judge nuanced writing quality.
- The prototype stores experiment history locally in SQLite and has no authentication or multi-user support.
- The baseline/verified comparison is an early prompt-and-verification experiment, not a complete factorial design.
- Token cost is unknown unless verified provider prices are configured.

The next research iteration should add more human-reviewed cases, measure grader agreement, repeat runs for stochasticity, and document failure categories before making performance claims.
