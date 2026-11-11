"""Run matched live baseline-versus-verified WorkflowBench experiments.

This command makes paid Responses API calls. Keep the first run small, inspect
the saved traces, and only then increase the case limit or repetitions.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openai import OpenAI

from .agents import run_live_agent
from .analytics import mcnemar_exact, summarise_runs
from .dataset import BENCHMARK_VERSION, load_dataset
from .evaluator import evaluate_run
from .tools import Sandbox


STRATEGIES = ("baseline", "verified")


def _write_results_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write rows with a union schema because agents expose different metrics."""
    if not rows:
        return
    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_comparison_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarise each agent separately and pair repeated trials by stable pair ID."""
    output: dict[str, Any] = {}
    for agent_type in sorted({row["agent_type"] for row in rows}):
        agent_rows = [row for row in rows if row["agent_type"] == agent_type]
        summaries: dict[str, Any] = {}
        paired: dict[str, list[dict[str, Any]]] = {}
        for strategy in STRATEGIES:
            selected = [row for row in agent_rows if row["strategy"] == strategy]
            metrics = [row["metrics"] for row in selected]
            summaries[strategy] = summarise_runs(metrics)
            paired[strategy] = [
                {**row["metrics"], "case_id": row["pair_id"]} for row in selected
            ]
        comparison = mcnemar_exact(paired["baseline"], paired["verified"])
        output[agent_type] = {
            "by_strategy": summaries,
            "paired_comparison": comparison,
        }
    return output


def _selected_cases(agent: str, split: str, limit: int) -> list[dict[str, Any]]:
    agents = {"knowledge", "workflow"} if agent == "both" else {agent}
    cases = [
        case for case in load_dataset()
        if case["agent_type"] in agents and case["split"] == split
    ]
    selected: list[dict[str, Any]] = []
    for agent_type in sorted(agents):
        selected.extend(
            [case for case in cases if case["agent_type"] == agent_type][:limit]
        )
    if not selected:
        raise ValueError(f"No benchmark cases found for agent={agent!r}, split={split!r}.")
    return selected


def run_comparison(
    model: str,
    agent: str,
    split: str,
    cases_per_agent: int,
    repetitions: int,
    output_dir: str | Path,
) -> dict[str, Any]:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set. Add it as a GitHub Actions secret.")
    if cases_per_agent < 1 or cases_per_agent > 8:
        raise ValueError("cases_per_agent must be between 1 and 8.")
    if repetitions < 1 or repetitions > 3:
        raise ValueError("repetitions must be between 1 and 3.")

    cases = _selected_cases(agent, split, cases_per_agent)
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    results: list[dict[str, Any]] = []
    traces: list[dict[str, Any]] = []

    for case in cases:
        allow_writes = case["agent_type"] == "workflow"
        for repetition in range(1, repetitions + 1):
            # Alternate strategy order across repeats to reduce simple order effects.
            order = STRATEGIES if repetition % 2 else tuple(reversed(STRATEGIES))
            pair_id = f"{case['id']}:repeat-{repetition}"
            for strategy in order:
                sandbox = Sandbox()
                run = run_live_agent(
                    case,
                    sandbox,
                    client,
                    model,
                    strategy=strategy,
                    allow_writes=allow_writes,
                )
                metrics = evaluate_run(case, run, sandbox)
                metrics.update({
                    "model": model,
                    "allow_writes": allow_writes,
                    "dataset_version": BENCHMARK_VERSION,
                    "repetition": repetition,
                    "pair_id": pair_id,
                })
                results.append({
                    "agent_type": case["agent_type"],
                    "strategy": strategy,
                    "repetition": repetition,
                    "pair_id": pair_id,
                    "metrics": metrics,
                })
                traces.append({
                    "agent_type": case["agent_type"],
                    "strategy": strategy,
                    "repetition": repetition,
                    "pair_id": pair_id,
                    "run": run.to_dict(),
                })

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "configuration": {
            "model": model,
            "agent": agent,
            "split": split,
            "cases_per_agent": cases_per_agent,
            "repetitions": repetitions,
            "strategies": list(STRATEGIES),
            "dataset_version": BENCHMARK_VERSION,
            "model_run_count": len(results),
            "workflow_writes_enabled_only_in_disposable_sandbox": True,
        },
        "agents": build_comparison_summary(results),
        "failed_runs": sum(
            1 for trace in traces if trace["run"]["status"] != "completed"
        ),
        "interpretation": (
            "Exploratory pilot only. Synthetic starter cases and a small sample do not "
            "support broad or statistically conclusive claims."
        ),
    }

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (destination / "traces.json").write_text(
        json.dumps(traces, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    flattened = [
        {
            "agent_type": row["agent_type"],
            "strategy": row["strategy"],
            "repetition": row["repetition"],
            "pair_id": row["pair_id"],
            **row["metrics"],
        }
        for row in results
    ]
    if flattened:
        _write_results_csv(destination / "results.csv", flattened)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run matched live baseline-versus-verified WorkflowBench experiments."
    )
    parser.add_argument("--model", default=os.getenv("OPENAI_MODEL", "gpt-6-luna"))
    parser.add_argument("--agent", choices=["knowledge", "workflow", "both"], default="both")
    parser.add_argument("--split", choices=["development", "evaluation"], default="development")
    parser.add_argument("--cases-per-agent", type=int, default=2)
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--output-dir", default="artifacts/live-experiment")
    args = parser.parse_args()

    try:
        summary = run_comparison(
            model=args.model,
            agent=args.agent,
            split=args.split,
            cases_per_agent=args.cases_per_agent,
            repetitions=args.repetitions,
            output_dir=args.output_dir,
        )
    except Exception as exc:
        parser.exit(2, f"Experiment failed: {type(exc).__name__}: {exc}\n")

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if summary["failed_runs"]:
        print(
            f"Warning: {summary['failed_runs']} model run(s) failed. "
            "Inspect traces.json in the uploaded artifact."
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
