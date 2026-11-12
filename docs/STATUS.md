# WorkflowBench status

## Implemented

- Knowledge & Research Agent and Workflow Execution Agent with isolated tool allowlists.
- OpenAI Responses API runner and Gemini Chat Completions runner using Google's OpenAI-compatible endpoint.
- Strict local Pydantic argument validation, disposable in-memory workspace and source-document sandbox.
- Explicit write approval, unsent message drafts, no delete tool and incident-closure recovery precondition.
- 24 labelled synthetic benchmark scenarios (12 per agent; 8 development and 16 held-out evaluation).
- Deterministic graders, baseline and verified prompt strategies, trace capture and SQLite history for live model runs.
- Offline fixture-driven simulation for all 24 scenarios, with separate JSON/CSV/trace artifacts and zero model or network calls.
- Union-schema CSV export so Knowledge and Workflow metric columns can coexist.
- Streamlit dashboard modes for scripted walkthrough, local simulation and live model runs.
- CLI commands for listing cases, demos, local simulation, individual model runs and matched baseline-versus-verified comparisons.
- Configuration-aware dashboards and matched statistical summaries.
- Learning, architecture, evaluation, research and free-run documentation.

## Verification

- Latest GitHub Actions test run: **33 passed**.
- Python compilation passed for the app, package and tests.
- All 24 deterministic local simulation fixtures pass their pipeline grader checks.
- The local simulation records no model usage, no network requests and no API cost. Its results are pipeline validation only, not model performance evidence.
- Fake Responses API and fake Gemini Chat Completions clients exercise the tool-calling loops without making paid or external API calls.

## Not yet verified

- A successful real Gemini API run has not yet been performed. It requires a Gemini API key from Google AI Studio; the free tier has quotas and its data-use conditions.
- The earlier OpenAI live attempt did not produce valid benchmark results: the OpenAI project had no remaining API credits, and the CSV export bug has since been fixed.
- Streamlit has been compiled by CI but not manually launched in this environment.
- No model-performance improvement, cost saving or market opportunity has been measured.
- The benchmark is a small synthetic pilot and is not representative of production traffic.

## Next research milestones

1. Run the offline simulation locally and inspect its traces.
2. Configure a Gemini API key using the free tier without enabling paid billing.
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
- The no-cost Gemini matched-run path is currently available through the local CLI and dashboard, not through that OpenAI-specific Actions workflow.

For the no-cost workflow, see [FREE_LOCAL_AND_GEMINI_RUNS.md](FREE_LOCAL_AND_GEMINI_RUNS.md).
