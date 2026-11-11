# WorkflowBench v0.1.1 Status

## Implemented
- Two agent types with a shared Responses API tool-calling loop.
- Strict JSON Schema function definitions and strict local Pydantic argument validation.
- Disposable in-memory document and workspace sandbox.
- Agent-specific tool allowlists, explicit write approval, no-send drafts, no-delete tool surface and incident-closure precondition.
- 24 labelled synthetic benchmark cases (12 per agent; 8 development and 16 held-out evaluation).
- Deterministic graders; knowledge task success requires retrieval of the full source document.
- Baseline and verified prompt strategies.
- Observable tool traces, token and latency capture, and local SQLite run history.
- Model ID, benchmark version and write-approval setting stored with each run.
- Configuration-aware dashboard comparisons.
- Streamlit dashboard, CLI, scripted walkthrough and statistical helpers.
- Learning, architecture, evaluation and research documentation.

## Verification completed locally
- 24 automated tests passed.
- Python compilation passed for app, package and test files.
- Scripted knowledge and workflow walkthroughs ran successfully.
- The fake Responses client exercises tool-calling without paid API calls.

## Not yet verified
- No live Responses API call has been made because no API key was supplied.
- Streamlit has not been launched in this environment.
- GitHub Actions must run on the updated commit to verify the hosted environment.
- No model-performance improvement, cost saving or market opportunity has been measured.
- The benchmark is a small synthetic pilot and is not representative of production traffic.

## Next research milestones
1. Run a small live development batch for both agents and inspect each trace.
2. Review grader disagreements and false positives/negatives against human labels.
3. Expand the benchmark with human-reviewed cases, including prompt injection and ambiguous record matches.
4. Run matched baseline/verified experiments with repeated trials and report uncertainty and operating cost.
5. Complete the competitive landscape and commercial assessment only after the evidence base is stronger.

## Repository
Source, tests and documentation are maintained at https://github.com/Aadith55/WorkflowBench.
