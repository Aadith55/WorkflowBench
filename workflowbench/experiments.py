"""Experiment orchestration: fresh sandbox, run, grade and save."""
from typing import Any

from .agents import run_live_agent
from .dataset import BENCHMARK_VERSION
from .evaluator import evaluate_run
from .storage import save_run
from .tools import Sandbox


def run_one_case(
    case: dict[str, Any],
    client: Any,
    model: str,
    strategy: str = "baseline",
    allow_writes: bool = False,
    save: bool = True,
    provider: str = "openai",
):
    """Run one scenario with OpenAI Responses or Gemini Chat Completions."""
    sandbox = Sandbox()
    if provider == "openai":
        runner = run_live_agent
    elif provider == "gemini":
        from .gemini_agent import run_gemini_agent

        runner = run_gemini_agent
    else:
        raise ValueError("provider must be 'openai' or 'gemini'.")

    run = runner(
        case, sandbox, client, model, strategy=strategy, allow_writes=allow_writes
    )
    metrics = evaluate_run(case, run, sandbox)
    metrics.update({
        "model": model,
        "provider": provider,
        "allow_writes": bool(allow_writes),
        "dataset_version": BENCHMARK_VERSION,
    })
    if save:
        save_run(metrics, run.to_dict())
    return run, metrics


def run_cases(
    cases: list[dict[str, Any]],
    client: Any,
    model: str,
    strategy: str = "baseline",
    allow_writes: bool = False,
    provider: str = "openai",
):
    results = []
    for case in cases:
        run, metrics = run_one_case(
            case,
            client,
            model,
            strategy,
            allow_writes,
            save=True,
            provider=provider,
        )
        results.append({"run": run.to_dict(), "metrics": metrics})
    return results
