"""WorkflowBench dashboard. Start with: streamlit run app.py"""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from workflowbench.analytics import mcnemar_exact
from workflowbench.dataset import load_dataset
from workflowbench.demo import run_scripted_walkthrough
from workflowbench.experiments import run_one_case
from workflowbench.storage import recent_runs

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

load_dotenv()
st.set_page_config(page_title="WorkflowBench", page_icon="🧪", layout="wide")
st.title("WorkflowBench")
st.caption(
    "A research prototype for AI workflow orchestration, evaluation and operational trade-offs."
)

with st.sidebar:
    st.header("Run configuration")
    run_mode = st.radio(
        "Mode",
        [
            "Scripted walkthrough",
            "Local simulation (no LLM)",
            "Live model run",
        ],
        index=0,
    )
    agent_type = st.selectbox(
        "Agent",
        ["knowledge", "workflow"],
        format_func=lambda value: (
            "Knowledge & Research Agent"
            if value == "knowledge"
            else "Workflow Execution Agent"
        ),
    )
    strategy = st.selectbox(
        "Strategy",
        ["baseline", "verified"],
        help="Verified adds explicit retrieval / post-action checks to the system instructions.",
    )
    allow_writes = st.checkbox(
        "Allow writes to the disposable local sandbox",
        value=False,
        help="Required for live workflow task creation, status updates and message drafts. "
        "No external system is connected.",
    )

    api_key_input = ""
    model = ""
    provider = "ollama"
    if run_mode == "Live model run":
        provider_label = st.selectbox(
            "Model provider",
            [
                "Ollama (local, no API key)",
                "Gemini API (free tier)",
                "OpenAI API",
            ],
            help=(
                "Ollama runs on this computer and does not require an API key. "
                "Gemini free-tier eligibility and quotas vary. OpenAI API calls may require paid credits."
            ),
            index=0,
        )
        if provider_label == "Ollama (local, no API key)":
            provider = "ollama"
            model = st.text_input(
                "Local Ollama model",
                value=os.getenv("OLLAMA_MODEL", "qwen3:4b"),
            )
            st.caption(
                "Install Ollama and download the model first. Keep the Ollama server running. "
                "Prompts and tool results are sent only to your local Ollama server."
            )
        elif provider_label == "Gemini API (free tier)":
            provider = "gemini"
            api_key_input = st.text_input(
                "Gemini API key",
                value=os.getenv("GEMINI_API_KEY", ""),
                type="password",
            )
            model = st.text_input(
                "Gemini model",
                value=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
            )
            st.caption(
                "Free-tier access is not guaranteed for every project, and quotas apply. "
                "Google may use free-tier API content to improve its products. "
                "WorkflowBench sends only synthetic example data."
            )
        else:
            provider = "openai"
            api_key_input = st.text_input(
                "OpenAI API key",
                value=os.getenv("OPENAI_API_KEY", ""),
                type="password",
            )
            model = st.text_input(
                "Model",
                value=os.getenv("OPENAI_MODEL", "gpt-6-luna"),
            )

cases = load_dataset()
agent_cases = [case for case in cases if case["agent_type"] == agent_type]
case_by_id = {case["id"]: case for case in agent_cases}

st.subheader("Benchmark overview")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Starter scenarios", len(cases))
col2.metric("Knowledge tasks", sum(case["agent_type"] == "knowledge" for case in cases))
col3.metric("Workflow tasks", sum(case["agent_type"] == "workflow" for case in cases))
col4.metric("Held-out scenarios", sum(case["split"] == "evaluation" for case in cases))

st.info(
    "The first benchmark is intentionally small so you can understand every scenario. "
    "Results from this starter dataset are exploratory, not broad claims about agent capability."
)

if run_mode == "Scripted walkthrough":
    st.info(
        "This is a fixed teaching example (K01 or W01). It does not run the selected "
        "benchmark case or call an LLM."
    )
    if st.button("Run scripted walkthrough", type="primary"):
        run, _ = run_scripted_walkthrough(agent_type)
        st.session_state["latest_demo"] = run.to_dict()
        st.session_state.pop("latest_live", None)
        st.session_state.pop("latest_simulation", None)

elif run_mode == "Local simulation (no LLM)":
    st.warning(
        "This is an oracle-driven fixture simulation. It uses the benchmark's expected "
        "labels to stage known tool calls. It validates the sandbox and grading pipeline, "
        "not model performance."
    )
    selected_id = st.selectbox(
        "Choose a benchmark task",
        options=[case["id"] for case in agent_cases],
        format_func=lambda case_id: (
            f"{case_id} · {case_by_id[case_id]['split']} · {case_by_id[case_id]['category']}"
        ),
    )
    selected_case = case_by_id[selected_id]
    with st.expander("Task and expected evaluation criteria", expanded=True):
        st.write(selected_case["task"])
        st.json(selected_case["expected"])

    if st.button("Run local simulation", type="primary"):
        from workflowbench.simulation import simulate_case

        run, sandbox, metrics = simulate_case(selected_case)
        st.session_state["latest_simulation"] = {
            "run": run.to_dict(),
            "metrics": metrics,
            "sandbox": sandbox.state,
        }
        st.session_state.pop("latest_demo", None)
        st.session_state.pop("latest_live", None)

else:
    selected_id = st.selectbox(
        "Choose a benchmark task",
        options=[case["id"] for case in agent_cases],
        format_func=lambda case_id: (
            f"{case_id} · {case_by_id[case_id]['split']} · {case_by_id[case_id]['category']}"
        ),
    )
    selected_case = case_by_id[selected_id]
    with st.expander("Task and expected evaluation criteria", expanded=True):
        st.write(selected_case["task"])
        st.json(selected_case["expected"])

    if st.button(
        "Run selected live task",
        type="primary",
        disabled=(provider != "ollama" and not api_key_input) or not model.strip(),
    ):
        st.session_state.pop("latest_live", None)
        try:
            from openai import OpenAI

            if provider == "gemini":
                client = OpenAI(
                    api_key=api_key_input,
                    base_url=GEMINI_BASE_URL,
                )
            elif provider == "ollama":
                client = OpenAI(
                    api_key="ollama",
                    base_url=os.getenv(
                        "OLLAMA_BASE_URL", "http://localhost:11434/v1/"
                    ),
                )
            else:
                client = OpenAI(api_key=api_key_input)

            with st.spinner("Running the selected case..."):
                run, metrics = run_one_case(
                    selected_case,
                    client,
                    model,
                    strategy,
                    allow_writes,
                    save=True,
                    provider=provider,
                )
            st.session_state["latest_live"] = {
                "run": run.to_dict(),
                "metrics": metrics,
            }
            st.session_state.pop("latest_demo", None)
            st.session_state.pop("latest_simulation", None)
        except Exception as exc:
            st.error(f"Could not start the live run: {type(exc).__name__}: {exc}")

if "latest_demo" in st.session_state:
    demo = st.session_state["latest_demo"]
    st.subheader("Scripted walkthrough trace")
    st.warning(
        "Walkthrough only: calls are scripted to teach the execution flow. "
        "No model was queried and no evaluation score was recorded."
    )
    st.write(demo["final_output"])
    st.dataframe(pd.DataFrame(demo["trace"]), use_container_width=True, hide_index=True)

if "latest_simulation" in st.session_state:
    latest = st.session_state["latest_simulation"]
    st.subheader("Local simulation result")
    st.warning(
        "Fixture-driven simulation only. This is not an LLM result and must not be "
        "reported as model performance."
    )
    metrics = latest["metrics"]
    a, b, c = st.columns(3)
    a.metric("Fixture grader", "PASS" if metrics["task_success"] else "FAIL")
    b.metric("Tool F1", f"{metrics.get('tool_f1', 0):.2f}")
    c.metric("Sandbox mutations", metrics.get("sandbox_mutations", 0))
    st.write(latest["run"]["final_output"] or latest["run"].get("error", "No output."))
    with st.expander("Inspect simulation trace"):
        st.dataframe(
            pd.DataFrame(latest["run"]["trace"]),
            use_container_width=True,
            hide_index=True,
        )
    with st.expander("Inspect final disposable sandbox state"):
        st.json(latest["sandbox"])
    st.json(metrics)

if "latest_live" in st.session_state:
    latest = st.session_state["latest_live"]
    st.subheader("Live model result")
    metrics = latest["metrics"]
    a, b, c, d = st.columns(4)
    a.metric("Task success", "PASS" if metrics["task_success"] else "FAIL")
    b.metric("Tool F1", f"{metrics.get('tool_f1', 0):.2f}")
    c.metric("Latency", f"{metrics.get('latency_ms', 0):.0f} ms")
    d.metric("Tokens", metrics.get("input_tokens", 0) + metrics.get("output_tokens", 0))
    if metrics.get("estimated_cost_usd") is None:
        st.caption(
            "Provider-reported token usage is recorded. Cost is not estimated unless "
            "verified prices are configured."
        )
    else:
        st.caption(f"Estimated API cost: ${metrics['estimated_cost_usd']:.6f}")
    if metrics.get("provider") == "gemini":
        st.caption(
            "Gemini free-tier eligibility, quotas and data-use terms apply. Check current status in AI Studio."
        )
    elif metrics.get("provider") == "ollama":
        st.caption(
            "This run used a model on your local Ollama server. No third-party inference API was called."
        )
    st.markdown("**Final output**")
    st.write(latest["run"]["final_output"] or latest["run"].get("error", "No final response."))
    st.markdown("**Evaluation metrics**")
    st.json(metrics)
    with st.expander("Inspect complete execution trace"):
        st.dataframe(
            pd.DataFrame(latest["run"]["trace"]),
            use_container_width=True,
            hide_index=True,
        )

st.divider()
st.subheader("Experiment history")
history = recent_runs(limit=100)
if not history:
    st.caption(
        "No live model runs have been saved yet. Scripted walkthroughs and local "
        "simulations are intentionally kept out of model experiment history."
    )
else:
    rows = []
    for item in history:
        metrics = item["metrics"]
        rows.append(metrics | {
            "created_at": item["created_at"],
            "run_id": item["id"],
            "model": metrics.get("model", "(not recorded)"),
            "provider": metrics.get("provider", "openai"),
            "allow_writes": bool(metrics.get("allow_writes", False)),
            "dataset_version": metrics.get("dataset_version", "(legacy)"),
        })
    history_df = pd.DataFrame(rows)
    st.dataframe(history_df, use_container_width=True, hide_index=True)

    strategy_rows = [row for row in rows if row.get("agent_type") == agent_type]
    if strategy_rows:
        st.markdown("**Observed task-success rate by strategy and configuration**")
        chart_frame = pd.DataFrame(strategy_rows).copy()
        chart_frame["configuration"] = chart_frame.apply(
            lambda row: (
                f"{row['provider']}:{row['model']} | writes={row['allow_writes']} | "
                f"{row['dataset_version']}"
            ),
            axis=1,
        )
        chart_data = chart_frame.pivot_table(
            index="configuration",
            columns="strategy",
            values="task_success",
            aggfunc="mean",
        )
        st.bar_chart(chart_data)

        config_keys = sorted({
            (
                row.get("provider", "openai"),
                row["model"],
                row["allow_writes"],
                row["dataset_version"],
            )
            for row in strategy_rows
        })
        for provider_name, model_name, writes_enabled, dataset_version in config_keys:
            config_rows = [
                row for row in strategy_rows
                if row.get("provider", "openai") == provider_name
                and row["model"] == model_name
                and row["allow_writes"] == writes_enabled
                and row["dataset_version"] == dataset_version
            ]
            base = [row for row in config_rows if row.get("strategy") == "baseline"]
            verified = [row for row in config_rows if row.get("strategy") == "verified"]
            if base and verified:
                st.markdown(
                    f"**Matched comparison: {provider_name}:{model_name} | "
                    f"writes={writes_enabled} | {dataset_version}**"
                )
                st.json(mcnemar_exact(base, verified))
                st.caption(
                    "Only matched case IDs from the same provider, model, dataset version "
                    "and write setting are compared. Interpret p-values cautiously with "
                    "this small starter benchmark."
                )

st.caption(
    "All benchmark data is synthetic and local. Tool actions modify only an in-memory "
    "copy of the example workspace; no external messages are sent."
)
