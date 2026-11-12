# WorkflowBench status

## Implemented

- Knowledge & Research Agent and Workflow Execution Agent with isolated tool allowlists.
- OpenAI Responses API runner, Gemini Chat Completions runner and local Ollama Chat Completions runner.
- Strict local Pydantic argument validation, disposable in-memory workspace and source-document sandbox.
- Explicit write approval in the dashboard and both CLI run paths, unsent message drafts, no delete tool and incident-closure recovery precondition.
- Benchmark `starter-v0.2`: 24 labelled synthetic scenarios (12 per agent; 8 development and 16 held-out evaluation).
- Source-grounding checks for Knowledge expected terms, duplicate-ID checks and occurrence-aware tool-call precision/recall/F1.
- Deterministic graders, baseline and verified prompt strategies, trace capture and SQLite history for live model runs.
- Offline fixture-driven simulation for all 24 scenarios, with separate JSON/CSV/trace artifacts and zero model or network calls.
- Union-schema CSV export so Knowledge and Workflow metric columns can coexist.
- Streamlit dashboard modes for scripted walkthrough, local simulation and live model runs with Ollama, Gemini or OpenAI.
- CLI commands for listing cases, demos, local simulation, individual model runs and matched baseline-versus-verified comparisons.
- Configuration-aware dashboards and matched statistical summaries.
- Learning, architecture, evaluation, research and free-run documentation.

## Verification

- The last confirmed full GitHub Actions run before v0.2 completed with **34 passing tests**. That run predates the v0.2 regression tests.
- Version v0.2 adds regression tests for source-grounded Knowledge labels, dataset-loader validation, repeated tool-call scoring and source-faithful fixture simulation.
- The CI workflow compiles the application and test modules, then runs `pytest` on pushes and pull requests.
- The offline simulation checks the full 24-case fixture pipeline. It records no model usage, no network requests and no API cost; its pass rate is pipeline validation only, not model performance evidence.
- A fake Ollama client test verifies the Chat Completions tool-calling loop and ensures the unsupported `tool_choice` request field is omitted for local Ollama.

## Provider options

### Ollama (preferred for zero API spend)

- Runs an open model locally through `http://localhost:11434/v1/`.
- No API key or hosted inference quota is required.
- The configured starter model is `qwen3:4b` (approximately 2.5 GB quantized download).
- First model download requires internet access; inference requests go to the local server.
- Model performance and speed depend on the computer's hardware.

### Gemini API free tier (optional)

- Requires a Gemini API key.
- Free-tier access depends on project eligibility and quotas; availability is not guaranteed for every project.
- Google may use free-tier content to improve products. Only synthetic WorkflowBench example data should be sent.

### OpenAI API (paid quota may apply)

- The earlier OpenAI live attempt did not produce valid benchmark results because the API project had no remaining credits; the CSV export bug has since been fixed.
- The manual GitHub Actions workflow remains an optional OpenAI Responses API path and now has a separate Boolean approval input for workflow writes. It is not required for local development or the zero-billing Ollama workflow.

## Not yet verified

- No successful live Gemini or Ollama model run has yet been performed.
- Ollama has not been launched on the user's computer; it requires installing Ollama and downloading the selected model locally.
- Streamlit has not been manually launched in the user's environment.
- The current v0.2 changes have not yet been confirmed by a new green CI result in this status record.
- No model-performance improvement, cost saving or market opportunity has been measured.
- The benchmark is a small synthetic pilot and is not representative of production traffic.

## Next research milestones

1. Run the offline simulation locally and inspect its traces.
2. Confirm Ollama can serve the selected Qwen3 model on the user's hardware.
3. Run a small matched baseline-versus-verified development experiment and inspect every trace.
4. Review grader disagreements and false positives/negatives against human labels.
5. Expand the benchmark with human-reviewed cases, including prompt injection, ambiguous record matches and conflicting sources.
6. Repeat experiments before making performance claims or drawing conclusions about operational value.

## Repository

Source, tests and documentation are maintained at https://github.com/Aadith55/WorkflowBench.

For the no-billing local setup, see [FREE_LOCAL_AND_GEMINI_RUNS.md](FREE_LOCAL_AND_GEMINI_RUNS.md).
