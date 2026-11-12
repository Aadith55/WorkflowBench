# Free local and Gemini runs

WorkflowBench now separates three types of execution. Keep their evidence distinct.

## 1. Offline fixture simulation

No API key, model, network request or billing account is required.

Run the complete starter dataset:

```bash
python -m workflowbench.cli simulate --agent both --split all
```

The runner reads each case's expected labels to stage a deterministic sequence of tool calls. It checks the sandbox, Pydantic tool validation, trace generation, deterministic grader and CSV/JSON export paths.

It writes:

- `simulation_summary.json`
- `simulation_results.csv`
- `simulation_traces.json`

The run is explicitly marked `deterministic_fixture_simulation`, records zero network requests and is not saved into the live-model SQLite history.

**Do not report its pass rate as model performance.** The fixture uses expected labels to construct known-good actions; it is an implementation and regression check only.

## 2. Gemini API free tier

Google AI Studio currently offers a free tier for selected Gemini API models. The current default configured here is `gemini-3.8-flash`. Availability, quotas and eligible models can change, so check the live quota panel before running more cases.

Official references:

- [Gemini API pricing and free-tier terms](https://ai.google.dev/gemini-api/docs/pricing)
- [OpenAI compatibility and function calling](https://ai.google.dev/gemini-api/docs/openai#function-calling)
- [Current model list](https://ai.google.dev/gemini-api/docs/models)
- [Rate limits and quota behaviour](https://ai.google.dev/gemini-api/docs/rate-limits)
- [Supported regions](https://ai.google.dev/gemini-api/docs/available-regions)
- [Google AI Studio API key page](https://aistudio.google.com/app/apikey)

India appears in Google's current supported-region list. The Gemini free tier lists free input and output tokens for eligible models, subject to quotas. Google also states that free-tier content may be used to improve its products. WorkflowBench only sends its synthetic sample documents and records, but never use this free-tier configuration with confidential, personal or customer data.

### Setup

1. Open [Google AI Studio API Keys](https://aistudio.google.com/app/apikey).
2. Create or select a project and create an API key. Do not enable paid billing for this free-tier setup.
3. Copy `.env.example` to `.env`.
4. Set:

   ```dotenv
   GEMINI_API_KEY=your_key_here
   GEMINI_MODEL=gemini-3.8-flash
   ```

5. Keep `.env` local. Never commit it or paste the key into chat, issues or source code.
6. Start the dashboard:

   ```bash
   streamlit run app.py
   ```

7. Choose **Live model run**, select **Gemini API (free tier)**, choose an agent and scenario, then run it. Workflow writes remain in a disposable in-memory sandbox and require the write checkbox.

### Matched baseline-versus-verified experiment

To evaluate both strategies against the same development cases:

```bash
python -m workflowbench.cli compare \
  --provider gemini \
  --agent both \
  --split development \
  --cases-per-agent 2 \
  --repetitions 1
```

This selects two Knowledge cases and two Workflow cases and runs each under baseline and verified instructions: eight model runs. A model run can make multiple API requests because it may need several tool-call turns.

The output directory contains:

- `summary.json`: configuration, per-agent summaries and paired outcomes.
- `results.csv`: one row per model run.
- `traces.json`: tool calls, tool results, final responses and run metadata.

A free-tier quota error, unavailable model or project restriction is a provider failure, not a zero-cost successful result. Inspect the traces and current quota panel before retrying. Do not switch to paid billing just to bypass a quota error.

## 3. OpenAI GitHub Actions workflow

The existing manual GitHub Actions workflow remains an OpenAI Responses API workflow and still requires `OPENAI_API_KEY` with available API quota. The Gemini local CLI path does not use that key and does not require paid OpenAI credits.
