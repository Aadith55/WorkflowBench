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

## 2. Local model with Ollama (no API key or inference billing)

This is the most predictable no-billing route for an actual model run. The model runs on your own computer; after downloading it, the chat and tool-call requests go to the local Ollama server at `localhost`, not a hosted inference API.

We configure **Qwen3:4B** as the starter model. Its Ollama library entry lists tool support and a 2.5 GB quantized download. The output quality and speed will depend on your hardware, and a 4B model may be less capable than larger hosted models. [Ollama model page](https://ollama.com/library/qwen3:4b)

### Setup on Windows

1. Install [Ollama for Windows](https://ollama.com/download/windows). Ollama supports Windows 10 or later and runs as a native app.
2. Open PowerShell and download the model:

   ```powershell
   ollama pull qwen3:4b
   ```

3. Confirm the model is installed:

   ```powershell
   ollama list
   ```

4. Make sure the Ollama app/server is running. The local OpenAI-compatible endpoint defaults to `http://localhost:11434/v1/`.
5. Pull the latest WorkflowBench code and install its dependencies:

   ```powershell
   git pull origin main
   pip install -e ".[dev]"
   ```

6. Run one live scenario through your local model:

   ```powershell
   python -m workflowbench.cli benchmark --provider ollama --agent knowledge --strategy baseline --split development --limit 1
   ```

7. Run a matched baseline-versus-verified pilot:

   ```powershell
   python -m workflowbench.cli compare --provider ollama --agent both --split development --cases-per-agent 2 --repetitions 1
   ```

This runs eight model trials across the four development scenarios. Each trial can involve multiple local model requests as tools are called. Output files are saved under `artifacts/live-experiment/`.

No `OLLAMA_API_KEY` is needed. The client uses a placeholder key because the OpenAI Python client requires a non-empty value; Ollama's local server ignores it. WorkflowBench does not call a cloud API when the provider is `ollama`.

If your computer cannot run Qwen3:4B comfortably, we can select a smaller model after checking its tool-calling support. Smaller models may make more tool-selection and argument errors, which is useful to measure but should be reported honestly.

Official references:

- [Ollama Windows download](https://ollama.com/download/windows)
- [Ollama OpenAI compatibility](https://github.com/ollama/ollama/blob/main/docs/api/openai-compatibility.mdx)
- [Qwen3:4B model and tool support](https://ollama.com/library/qwen3:4b)

## 3. Gemini API free tier

Google AI Studio offers a free tier for selected Gemini API models. The current default configured here is `gemini-3.8-flash`. Free-tier eligibility is not guaranteed for every account or project: some recently reported projects show a free-tier unavailable restriction and return 403 unless billing is enabled. We will not enable billing to bypass this. Check the AI Studio project status and quota panel first.

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

## 4. OpenAI GitHub Actions workflow

The existing manual GitHub Actions workflow remains an OpenAI Responses API workflow and still requires `OPENAI_API_KEY` with available API quota. The Gemini local CLI path does not use that key and does not require paid OpenAI credits.
