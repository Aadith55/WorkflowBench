"""Load and sanity-check the versioned JSONL benchmark."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
BENCHMARK_VERSION = "starter-v0.1"

def load_dataset(path: str | Path | None = None) -> list[dict[str, Any]]:
    source = Path(path) if path else DATA_DIR / "benchmark.jsonl"
    cases, seen = [], set()
    with source.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                case = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_no}: {exc.msg}") from exc
            required = {"id", "agent_type", "split", "task", "expected"}
            missing = required - case.keys()
            if missing:
                raise ValueError(f"Line {line_no} missing: {', '.join(sorted(missing))}")
            if case["id"] in seen:
                raise ValueError(f"Duplicate case ID: {case['id']}")
            if case["agent_type"] not in {"knowledge", "workflow"}:
                raise ValueError(f"Unsupported agent type on line {line_no}")
            if case["split"] not in {"development", "evaluation"}:
                raise ValueError(f"Unsupported split on line {line_no}")
            seen.add(case["id"])
            cases.append(case)
    return cases

def get_case(case_id: str, cases: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    for case in cases or load_dataset():
        if case["id"] == case_id:
            return case
    raise KeyError(f"Unknown benchmark case: {case_id}")
