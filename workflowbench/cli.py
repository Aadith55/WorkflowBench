"""Command-line entry point for demos, local simulations and live batches."""
import argparse
import os

from dotenv import load_dotenv

from .dataset import load_dataset
from .demo import run_scripted_walkthrough
from .experiments import run_cases


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
    bench.add_argument("--strategy", choices=["baseline", "verified"], default="baseline")
    bench.add_argument(
        "--split", choices=["development", "evaluation"], default="development"
    )
    bench.add_argument("--limit", type=int, default=2)
    bench.add_argument("--allow-writes", action="store_true")

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

    if not os.getenv("OPENAI_API_KEY"):
        parser.error("Set OPENAI_API_KEY in .env before an OpenAI live run.")
    from openai import OpenAI

    cases = [
        case for case in load_dataset()
        if case["agent_type"] == args.agent and case["split"] == args.split
    ][:max(1, min(args.limit, 12))]
    results = run_cases(
        cases,
        OpenAI(),
        os.getenv("OPENAI_MODEL", "gpt-6-luna"),
        args.strategy,
        args.allow_writes,
    )
    print(
        f"Completed {len(results)} runs; successes: "
        f"{sum(item['metrics']['task_success'] for item in results)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
