"""Command-line entry point for demos and small live batches."""
import argparse, os
from dotenv import load_dotenv
from .dataset import load_dataset
from .demo import run_scripted_walkthrough
from .experiments import run_cases

def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Run WorkflowBench")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list")
    demo = sub.add_parser("demo"); demo.add_argument("--agent", choices=["knowledge","workflow"], default="knowledge")
    bench = sub.add_parser("benchmark"); bench.add_argument("--agent", choices=["knowledge","workflow"], required=True)
    bench.add_argument("--strategy", choices=["baseline","verified"], default="baseline")
    bench.add_argument("--split", choices=["development","evaluation"], default="development")
    bench.add_argument("--limit", type=int, default=2); bench.add_argument("--allow-writes", action="store_true")
    args = parser.parse_args()
    if args.command == "list":
        for c in load_dataset(): print(c["id"], c["agent_type"], c["split"], c.get("category",""))
        return 0
    if args.command == "demo":
        run, _ = run_scripted_walkthrough(args.agent)
        print(run.case_id, "| SCRIPTED WALKTHROUGH ONLY")
        for e in run.trace: print(e.index, e.event_type, e.tool_name or "", e.message)
        print(run.final_output); return 0
    if not os.getenv("OPENAI_API_KEY"): parser.error("Set OPENAI_API_KEY in .env before a live run.")
    from openai import OpenAI
    cases = [c for c in load_dataset() if c["agent_type"] == args.agent and c["split"] == args.split][:max(1,min(args.limit,12))]
    results = run_cases(cases, OpenAI(), os.getenv("OPENAI_MODEL","gpt-6-luna"), args.strategy, args.allow_writes)
    print(f"Completed {len(results)} runs; successes: {sum(x['metrics']['task_success'] for x in results)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
