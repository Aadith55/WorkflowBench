# WorkflowBench status

## Implemented

- Knowledge & Research Agent and Workflow Execution Agent with isolated tool allowlists.
- OpenAI Responses API runner, Gemini Chat Completions runner and local Ollama Chat Completions runner.
- Strict local Pydantic argument validation, disposable in-memory workspace and source-document sandbox.
- Explicit write approval, unsent message drafts, no delete tool and incident-closure recovery precondition.
- 24 labelled synthetic benchmark scenarios (12 per agent; 8 development and 16 held-out evaluation).
- Deterministic graders, baseline and verified prompt strategies, trace capture and SQLite history for live model runs.
- Offline fixture-driven simulation for all 24 scenarios, with separate JSON/CSV/trace artifacts and zero model or network calls.
- Union-schema CSV export so Knowledge and Workflow metric columns can coexist.
- Streamlit dashboard modes for scripted walkthrough, local simulation and live model runs with Ollama, Gemini or OpenAI.
- CLI commands for listing cases, demos, local simulation, individual model runs and matched baseline-versus-verified comparisons.
- Configuration-aware dashboards and matched statistical summaries.
- Learning, architecture, evaluation, research and free-run documentation.

## Verification

- Previous full GitHub Actions run: **33 passed** before adding the Ollama adapter.
- The CI suite includes full 24-case deterministic simulation, fake OpenAI/Gemini tool-calling tests, CSV schema coverage and sandbox safety checks.
- A new fake Ollama client test verifies the tool-calling loop and ensures the unsupported `tool_choice` request field is omitted for local Ollama.
- Latest CI status should be checked on the current `main` commit before starting a live local-model experiment.
- The local simulation records no model usage, no network requests and no API cost. Its pass rate is pipeline validation only, not model performance evidence.

## Provider options

### Ollama (preferred for zero API spend)

- Runs an open model locally through `http://localhost:11434/v1/`.
- No API key or hosted inference quota is required.
- The configured starter model is `qwen3:4b` (approximately 2.5 GB quantized download).
- First model download requires internet access; inference requests go to the local server.
- Model performance and speed depend on the user's hardware. The model is smaller than the hosted Gemini/OpenAI options.

### Gemini API free tier (optional)

- Requires a Gemini API key.
- Google lists free input/output tokens for eligible models and projects, subject to quotas.
- Eligibility is not guaranteed for every project. Some projects may show free tier unavailable or return 403.
- Google may use free-tier content to improve products. Only synthetic WorkflowBench example data should be sent.

### OpenAI API (paid quota may apply)

- The earlier OpenAI live attempt did not produce valid benchmark results: the API project had no remaining credits, and the CSV export bug has since been fixed.
- The existing GitHub Actions workflow remains configured for OpenAI Responses API.

## Not yet verified

- No successful live Gemini or Ollama model run has yet been performed.
- Ollama has not been launched on the user's computer; it requires installing Ollama and downloading the selected model locally.
- Streamlit has been compiled by CI but not manually launched in the user's environment.
- No model-performance improvement, cost saving or market opportunity has been measured.
- The benchmark is a small synthetic pilot and is not representative of production traffic.

## Next research milestones

1. Run the offline simulation locally and inspect its traces.
2. Confirm Ollama can serve the selected Qwen3 model on the user's hardware.
3. Run a small matched baseline-versus-verified development experiment and inspect every trace.
4. Review grader disagreements and false positives/negatives against human labels.
5. Expand the benchmark with human-reviewed cases, including prompt injection and ambiguous record matches.
6. Repeat experiments before making performance claims or drawing conclusions about operational value.

## Repository

Source, tests and documentation are maintained at https://github.com/Aadith55/WorkflowBench.

## Existing GitHub Actions workflow

- The manual GitHub Actions workflow remains an OpenAI Responses API workflow and uses the `OPENAI_API_KEY` repository secret.
- Its default pilot selects two development cases per agent under baseline and verified strategies (eight model runs).
- It uploads a summary, CSV metrics and observable execution traces.
- The no-cost Ollama matched-run path is currently available through the local CLI and dashboard, not through that OpenAI-specific Actions workflow.

For the no-cost workflow, see [FREE_LOCAL_AND_GEMINI_RUNS.md](FREE_LOCAL_AND_GEMINI_RUNS.md).
