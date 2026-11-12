"""Command-line entry point for demos, local simulations and live batches."""
import argparse
import os

from dotenv import load_dotenv
from openai import OpenAI

from .dataset import load_dataset
from .demo import run_scripted_walkthrough
from .experiments import run_cases


GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Run WorkflowBench")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list")

    demo = sub.add_parser("demo")
    demo.add_argument("--agent", choices=["knowledge", "workflow"], default="knowledge")

    simulation = sub.add_parser(
        "simulate",
        help="Run the free deterministic fixture simulation (no LLM or network calls).",
    )
    simulation.add_argument(
        "--agent", choices=["knowledge", "workflow", "both"], default="both"
    )
    simulation.add_argument(
        "--split", choices=["development", "evaluation", "all"], default="development"
    )
    simulation.add_argument("--limit", type=int, default=12)
    simulation.add_argument("--output-dir", default="artifacts/local-simulation")

    bench = sub.add_parser("benchmark")
    bench.add_argument("--agent", choices=["knowledge", "workflow"], required=True)
    bench.add_argument("--provider", choices=["ollama", "gemini", "openai"], default="ollama")
    bench.add_argument("--model", default=None)
    bench.add_argument("--strategy", choices=["baseline", "verified"], default="baseline")
    bench.add_argument(
        "--split", choices=["development", "evaluation"], default="development"
    )
    bench.add_argument("--limit", type=int, default=2)
    bench.add_argument("--allow-writes", action="store_true")

    compare = sub.add_parser(
        "compare",
        help="Run matched baseline-versus-verified live model experiments.",
    )
    compare.add_argument("--provider", choices=["ollama", "gemini", "openai"], default="ollama")
    compare.add_argument("--model", default=None)
    compare.add_argument("--agent", choices=["knowledge", "workflow", "both"], default="both")
    compare.add_argument(
        "--split", choices=["development", "evaluation"], default="development"
    )
    compare.add_argument("--cases-per-agent", type=int, default=2)
    compare.add_argument("--repetitions", type=int, default=1)
    compare.add_argument("--output-dir", default="artifacts/live-experiment")

    args = parser.parse_args()
    if args.command == "list":
        for case in load_dataset():
            print(
                case["id"], case["agent_type"], case["split"],
                case.get("category", "")
            )
        return 0

    if args.command == "demo":
        run, _ = run_scripted_walkthrough(args.agent)
        print(run.case_id, "| SCRIPTED WALKTHROUGH ONLY")
        for event in run.trace:
            print(event.index, event.event_type, event.tool_name or "", event.message)
        print(run.final_output)
        return 0

    if args.command == "simulate":
        from .simulation import run_local_simulation

        summary = run_local_simulation(
            agent=args.agent,
            split=args.split,
            limit=args.limit,
            output_dir=args.output_dir,
        )
        print("LOCAL SIMULATION ONLY — no model was queried and no API cost was incurred.")
        print(f"Scenarios checked: {summary['configuration']['scenario_count']}")
        for agent_type, result in summary["by_agent"].items():
            print(
                f"{agent_type}: {result['grader_fixture_passes']}/"
                f"{result['cases']} fixture checks passed"
            )
        print(f"Artifacts: {args.output_dir}")
        print(summary["interpretation"])
        return 0

    if args.command == "compare":
        from .live_compare import run_comparison

        if args.provider == "gemini":
            model = args.model or os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
        elif args.provider == "ollama":
            model = args.model or os.getenv("OLLAMA_MODEL", "qwen3:4b")
        else:
            model = args.model or os.getenv("OPENAI_MODEL", "gpt-6-luna")
        summary = run_comparison(
            model=model,
            agent=args.agent,
            split=args.split,
            cases_per_agent=args.cases_per_agent,
            repetitions=args.repetitions,
            output_dir=args.output_dir,
            provider=args.provider,
        )
        print(
            f"Completed {summary['configuration']['model_run_count']} "
            f"{args.provider} model runs."
        )
        print(f"Artifacts: {args.output_dir}")
        print(summary["interpretation"])
        return 0

    if args.provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY", "")
        model = args.model or os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
        if not api_key:
            parser.error("Set GEMINI_API_KEY in .env to use the Gemini free tier.")
        client = OpenAI(api_key=api_key, base_url=GEMINI_BASE_URL)
    elif args.provider == "ollama":
        model = args.model or os.getenv("OLLAMA_MODEL", "qwen3:4b")
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1/")
        client = OpenAI(api_key="ollama", base_url=base_url)
    else:
        api_key = os.getenv("OPENAI_API_KEY", "")
        model = args.model or os.getenv("OPENAI_MODEL", "gpt-6-luna")
        if not api_key:
            parser.error("Set OPENAI_API_KEY in .env before an OpenAI API run.")
        client = OpenAI(api_key=api_key)

    cases = [
        case for case in load_dataset()
        if case["agent_type"] == args.agent and case["split"] == args.split
    ][:max(1, min(args.limit, 12))]
    results = run_cases(
        cases,
        client,
        model,
        args.strategy,
        args.allow_writes,
        provider=args.provider,
    )
    successes = sum(item["metrics"]["task_success"] for item in results)
    print(
        f"Completed {len(results)} {args.provider} runs; "
        f"task-success grades: {successes}"
    )
    print("Check the local SQLite history and execution traces in the dashboard.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
