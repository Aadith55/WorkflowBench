"""Load and sanity-check the versioned JSONL benchmark."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
BENCHMARK_VERSION = "starter-v0.2"


def load_dataset(path: str | Path | None = None) -> list[dict[str, Any]]:
    """Load benchmark cases and reject malformed or duplicate entries."""
    source = Path(path) if path else DATA_DIR / "benchmark.jsonl"
    cases: list[dict[str, Any]] = []
    seen: set[str] = set()

    with source.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                case = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_no}: {exc.msg}"
                ) from exc

            if not isinstance(case, dict):
                raise ValueError(f"Line {line_no} must contain a JSON object.")

            required = {"id", "agent_type", "split", "task", "expected"}
            missing = required - case.keys()
            if missing:
                raise ValueError(
                    f"Line {line_no} missing: {', '.join(sorted(missing))}"
                )

            case_id = case["id"]
            if not isinstance(case_id, str) or not case_id.strip():
                raise ValueError(f"Line {line_no} has an invalid case ID.")
            if case_id in seen:
                raise ValueError(f"Duplicate case ID: {case_id}")

            if case["agent_type"] not in {"knowledge", "workflow"}:
                raise ValueError(f"Unsupported agent type on line {line_no}")
            if case["split"] not in {"development", "evaluation"}:
                raise ValueError(f"Unsupported split on line {line_no}")
            if not isinstance(case["task"], str) or not case["task"].strip():
                raise ValueError(f"Line {line_no} has an empty or invalid task.")
            if not isinstance(case["expected"], dict):
                raise ValueError(f"Line {line_no} expected outcome must be an object.")

            seen.add(case_id)
            cases.append(case)

    return cases


def get_case(
    case_id: str, cases: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    for case in cases or load_dataset():
        if case["id"] == case_id:
            return case
    raise KeyError(f"Unknown benchmark case: {case_id}")
