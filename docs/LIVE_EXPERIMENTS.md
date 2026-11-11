# Running live WorkflowBench experiments

WorkflowBench includes a manual GitHub Actions workflow that runs matched baseline and verified strategies against the live OpenAI Responses API.

## One-time setup

1. Open the repository's **Settings**.
2. Go to **Secrets and variables -> Actions**.
3. Select **New repository secret**.
4. Set the name to `OPENAI_API_KEY` and paste your API key as the secret value.
5. Save it. Do not add the key to a source file, issue, pull request, or chat message.

The workflow reads the secret from the Actions environment. It is not printed in logs or saved in the results artifact.

## Run the first pilot

1. Open the repository's **Actions** tab.
2. Select **Live API experiment**.
3. Choose **Run workflow**.
4. Keep the defaults for the first run:
   - Model: `gpt-6-luna`
   - Agent: `both`
   - Split: `development`
   - Cases per agent: `2`
   - Repetitions: `1`
5. Start the workflow.

The default run evaluates two Knowledge cases and two Workflow cases under both baseline and verified strategies: eight model runs total. The Workflow Agent's writes are enabled only inside a fresh in-memory sandbox that is discarded after each case. No real email is sent and no external business system is changed.

## Get the results

When the workflow finishes, open the run and download the artifact named `workflowbench-live-experiment-...`. It contains:

- `summary.json`: per-agent success rates, Wilson intervals, latency/cost summaries and paired comparisons.
- `results.csv`: one row per model run for spreadsheet analysis.
- `traces.json`: complete observable tool-call and result traces for debugging.

A failed model run still produces an artifact where possible. Inspect `traces.json` before interpreting a score.

## Cost and limits

The default model is GPT-6 Luna. The workflow estimates token cost using the published per-million-token rates for the selected model. Treat this as an estimate, since provider pricing and account terms can change. The model, case count and repetition count are selectable; cases are capped at eight per agent and repetitions at three.

The first run is deliberately small. Inspect its traces and the grader behaviour before increasing the sample. The benchmark is synthetic and small, so results are exploratory, not evidence of general production performance.

For local use, install the project and set `OPENAI_API_KEY` in a local `.env` file, then run:

```bash
python -m workflowbench.live_compare --agent both --split development --cases-per-agent 2 --repetitions 1
```
