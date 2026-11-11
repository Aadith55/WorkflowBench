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

load_dotenv()
st.set_page_config(page_title="WorkflowBench", page_icon="🧪", layout="wide")
st.title("WorkflowBench")
st.caption("A research prototype for AI workflow orchestration, evaluation and operational trade-offs.")

with st.sidebar:
    st.header("Run configuration")
    run_mode = st.radio("Mode", ["Scripted walkthrough", "Live model run"], index=0)
    agent_type = st.selectbox("Agent", ["knowledge", "workflow"], format_func=lambda x: "Knowledge & Research Agent" if x == "knowledge" else "Workflow Execution Agent")
    strategy = st.selectbox("Strategy", ["baseline", "verified"], help="Verified adds explicit retrieval / post-action checks to the system instructions.")
    allow_writes = st.checkbox("Allow writes to the disposable local sandbox", value=False, help="Required for task creation, status updates and message drafts. No external system is connected.")
    api_key_input = ""
    if run_mode == "Live model run":
        api_key_input = st.text_input("API key", value=os.getenv("OPENAI_API_KEY", ""), type="password")
        model = st.text_input("Model", value=os.getenv("OPENAI_MODEL", "gpt-6-luna"))

cases = load_dataset()
agent_cases = [case for case in cases if case["agent_type"] == agent_type]
case_by_id = {case["id"]: case for case in agent_cases}

st.subheader("Benchmark overview")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Starter scenarios", len(cases))
col2.metric("Knowledge tasks", sum(c["agent_type"] == "knowledge" for c in cases))
col3.metric("Workflow tasks", sum(c["agent_type"] == "workflow" for c in cases))
col4.metric("Held-out scenarios", sum(c["split"] == "evaluation" for c in cases))

st.info("The first benchmark is intentionally small so you can understand every scenario. Results from this starter dataset are exploratory, not broad claims about agent capability.")

if run_mode == "Scripted walkthrough":
    st.info(
        "This is a fixed teaching example (K01 or W01). It does not run the selected benchmark case "
        "or call an LLM."
    )
    if st.button("Run scripted walkthrough", type="primary"):
        run, _ = run_scripted_walkthrough(agent_type)
        st.session_state["latest_demo"] = run.to_dict()
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

    if st.button("Run selected live task", type="primary", disabled=not api_key_input):
        st.session_state.pop("latest_live", None)
        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key_input)
            with st.spinner("Running the selected case..."):
                run, metrics = run_one_case(
                    selected_case, client, model, strategy, allow_writes, save=True
                )
            st.session_state["latest_live"] = {"run": run.to_dict(), "metrics": metrics}
            st.session_state.pop("latest_demo", None)
        except Exception as exc:
            st.error(f"Could not start the live run: {type(exc).__name__}: {exc}")

if "latest_demo" in st.session_state:
    demo = st.session_state["latest_demo"]
    st.subheader("Scripted walkthrough trace")
    st.warning("Walkthrough only: the calls below are scripted to teach the execution flow. No model was queried and no evaluation score was recorded.")
    st.write(demo["final_output"])
    st.dataframe(pd.DataFrame(demo["trace"]), use_container_width=True, hide_index=True)

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
        st.caption("Cost not estimated. Add verified input/output token prices to .env to calculate a cost estimate.")
    else:
        st.caption(f"Estimated API cost: ${metrics['estimated_cost_usd']:.6f}")
    st.markdown("**Final output**")
    st.write(latest["run"]["final_output"] or latest["run"].get("error", "No final response."))
    st.markdown("**Evaluation metrics**")
    st.json(metrics)
    with st.expander("Inspect complete execution trace"):
        st.dataframe(pd.DataFrame(latest["run"]["trace"]), use_container_width=True, hide_index=True)

st.divider()
st.subheader("Experiment history")
history = recent_runs(limit=100)
if not history:
    st.caption(
        "No live model runs have been saved yet. Try the scripted walkthrough first, "
        "then configure an API key for a real experiment."
    )
else:
    rows = []
    for item in history:
        metrics = item["metrics"]
        rows.append(metrics | {
            "created_at": item["created_at"],
            "run_id": item["id"],
            "model": metrics.get("model", "(not recorded)"),
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
                f"{row['model']} | writes={row['allow_writes']} | {row['dataset_version']}"
            ),
            axis=1,
        )
        chart_data = chart_frame.pivot_table(
            index="configuration", columns="strategy", values="task_success", aggfunc="mean"
        )
        st.bar_chart(chart_data)

        config_keys = sorted({
            (row["model"], row["allow_writes"], row["dataset_version"])
            for row in strategy_rows
        })
        for model_name, writes_enabled, dataset_version in config_keys:
            config_rows = [
                row for row in strategy_rows
                if row["model"] == model_name
                and row["allow_writes"] == writes_enabled
                and row["dataset_version"] == dataset_version
            ]
            base = [row for row in config_rows if row.get("strategy") == "baseline"]
            verified = [row for row in config_rows if row.get("strategy") == "verified"]
            if base and verified:
                st.markdown(
                    f"**Matched comparison: {model_name} | writes={writes_enabled} | "
                    f"{dataset_version}**"
                )
                st.json(mcnemar_exact(base, verified))
                st.caption(
                    "Only matched case IDs from the same model, dataset version and write setting "
                    "are compared. Interpret p-values cautiously with this small starter benchmark."
                )

st.caption("All data is synthetic and local. Tool actions modify only an in-memory copy of the example workspace; no external messages are sent.")
