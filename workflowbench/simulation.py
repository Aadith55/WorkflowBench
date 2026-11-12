"""Deterministic local rehearsal of the benchmark pipeline.

This fixture-driven runner exercises the sandbox, tool validation, trace capture,
deterministic grader and export path without calling any language model. It reads
the benchmark's expected labels to construct a known-good tool sequence, so its
scores are pipeline checks only and must never be reported as model performance.
"""
from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .dataset import BENCHMARK_VERSION, load_dataset
from .evaluator import evaluate_run
from .models import AgentRun, TraceEvent
from .tools import Sandbox


def _record_target(case: dict[str, Any], sandbox: Sandbox) -> str | None:
    expected = case["expected"]
    for update in expected.get("record_updates", []):
        return str(update["record_id"])
    for task in expected.get("created_tasks", []):
        return str(task["related_record_id"])

    explicit_id = re.search(r"REC-\d{3}", case["task"], flags=re.IGNORECASE)
    if explicit_id:
        return explicit_id.group(0).upper()

    task_text = case["task"].casefold()
    for record in sandbox.state.get("records", []):
        name = str(record.get("name", ""))
        if name and name.casefold() in task_text:
            return str(record["id"])
    return None


def _record_call(
    sandbox: Sandbox,
    trace: list[TraceEvent],
    name: str,
    arguments: dict[str, Any],
    agent_type: str,
    allow_writes: bool = False,
) -> Any:
    result, event_type = sandbox.call(
        name, arguments, agent_type, allow_writes=allow_writes
    )
    trace.append(TraceEvent(
        index=len(trace) + 1,
        event_type="tool_call",
        message=f"Local fixture invoked {name}.",
        tool_name=name,
        arguments=arguments,
    ))
    trace.append(TraceEvent(
        index=len(trace) + 1,
        event_type=event_type,
        message=f"{name} returned {event_type.replace('_', ' ')}.",
        tool_name=name,
        result=result,
    ))
    return result


def simulate_case(case: dict[str, Any]) -> tuple[AgentRun, Sandbox, dict[str, Any]]:
    """Execute one fixture-driven scenario without any model or network calls."""
    sandbox = Sandbox()
    trace: list[TraceEvent] = []
    agent_type = case["agent_type"]
    expected = case["expected"]
    final_output = ""

    try:
        if agent_type == "knowledge":
            required_ids = expected.get("required_doc_ids", [])
            if not required_ids:
                raise ValueError(f"{case['id']} has no required source document.")
            document_id = str(required_ids[0])
            document = next(
                (row for row in sandbox.documents if row["id"] == document_id), None
            )
            if document is None:
                raise ValueError(f"Fixture document {document_id} does not exist.")

            search = _record_call(
                sandbox,
                trace,
                "search_documents",
                {"query": document["title"], "limit": 5},
                agent_type,
            )
            found_ids = {
                row["id"] for row in search.get("results", [])
                if isinstance(row, dict) and "id" in row
            }
            if document_id not in found_ids:
                raise RuntimeError(
                    f"Fixture search did not find expected document {document_id}."
                )

            retrieved = _record_call(
                sandbox,
                trace,
                "get_document",
                {"document_id": document_id},
                agent_type,
            )
            if not isinstance(retrieved, dict) or retrieved.get("id") != document_id:
                raise RuntimeError(f"Could not retrieve full document {document_id}.")

            final_output = f'{retrieved["content"]} [{document_id}]'

        elif agent_type == "workflow":
            required_tools = expected.get("required_tools", [])
            if required_tools:
                target_id = _record_target(case, sandbox)
                search_query = target_id or case["task"]
                search = _record_call(
                    sandbox,
                    trace,
                    "search_records",
                    {"query": search_query, "limit": 5},
                    agent_type,
                    allow_writes=True,
                )
                found = [
                    row for row in search.get("results", [])
                    if isinstance(row, dict)
                ]
                target = next(
                    (row for row in found if row.get("id") == target_id), None
                )
                if target_id and target is not None and "get_record" in required_tools:
                    retrieved = _record_call(
                        sandbox,
                        trace,
                        "get_record",
                        {"record_id": target_id},
                        agent_type,
                        allow_writes=True,
                    )
                    if not isinstance(retrieved, dict) or retrieved.get("id") != target_id:
                        raise RuntimeError(f"Could not retrieve workspace record {target_id}.")
                elif "get_record" in required_tools and target_id:
                    raise RuntimeError(
                        f"Fixture search did not find expected workspace record {target_id}."
                    )

                completed_actions: list[str] = []
                for tool_name in required_tools:
                    if tool_name == "create_task":
                        for task in expected.get("created_tasks", []):
                            result = _record_call(
                                sandbox, trace, "create_task", task, agent_type,
                                allow_writes=True,
                            )
                            if not result.get("ok"):
                                raise RuntimeError(result.get("error", "Task creation failed."))
                            completed_actions.append(f'Created task {result["task"]["id"]}')
                    elif tool_name == "update_record":
                        for update in expected.get("record_updates", []):
                            arguments = {
                                "record_id": update["record_id"],
                                "status": update["status"],
                                "note": update.get("note_contains", ""),
                            }
                            result = _record_call(
                                sandbox, trace, "update_record", arguments, agent_type,
                                allow_writes=True,
                            )
                            if not result.get("ok"):
                                raise RuntimeError(result.get("error", "Record update failed."))
                            completed_actions.append(
                                f'Updated {update["record_id"]} to {update["status"]}'
                            )
                    elif tool_name == "draft_message":
                        for draft in expected.get("drafts", []):
                            subject_fragment = draft.get("subject_contains", "Update")
                            body_fragment = draft.get("body_contains", "update")
                            arguments = {
                                "recipient": draft["recipient"],
                                "subject": f"{subject_fragment} update",
                                "body": (
                                    f"Hello {draft['recipient']}, {body_fragment} "
                                    "details are ready for review. This is a draft only."
                                ),
                            }
                            result = _record_call(
                                sandbox, trace, "draft_message", arguments, agent_type,
                                allow_writes=True,
                            )
                            if not result.get("ok"):
                                raise RuntimeError(result.get("error", "Draft creation failed."))
                            completed_actions.append(
                                f'Created an unsent draft for {draft["recipient"]}'
                            )

                if completed_actions:
                    final_output = "; ".join(completed_actions) + (
                        ". All changes are confined to the disposable in-memory sandbox."
                    )
                elif target_id and target is None:
                    final_output = (
                        f"Record {target_id} was not found. No workspace changes were made."
                    )
                elif target_id == "REC-106":
                    final_output = (
                        "The incident was not closed because recovery validation is not recorded."
                    )
                else:
                    final_output = "No workspace changes were required or made."
            else:
                final_output = (
                    "Deletion is not available in the tool registry. "
                    "No record or audit history was changed."
                )
        else:
            raise ValueError(f"Unsupported agent type: {agent_type}")

        trace.append(TraceEvent(
            index=len(trace) + 1,
            event_type="final",
            message="Deterministic local simulation completed.",
            result=final_output,
        ))
        run = AgentRun(
            case_id=case["id"],
            agent_type=agent_type,
            strategy="local_simulation",
            status="completed",
            final_output=final_output,
            trace=trace,
        )
    except Exception as exc:
        trace.append(TraceEvent(
            index=len(trace) + 1,
            event_type="run_error",
            message=f"Local simulation stopped: {type(exc).__name__}: {exc}",
        ))
        run = AgentRun(
            case_id=case["id"],
            agent_type=agent_type,
            strategy="local_simulation",
            status="error",
            trace=trace,
            error=f"{type(exc).__name__}: {exc}",
        )

    metrics = evaluate_run(case, run, sandbox)
    metrics.update({
        "execution_mode": "deterministic_fixture_simulation",
        "model": None,
        "allow_writes": agent_type == "workflow",
        "dataset_version": BENCHMARK_VERSION,
        "oracle_driven_fixture": True,
    })
    return run, sandbox, metrics


def run_local_simulation(
    agent: str = "both",
    split: str = "development",
    limit: int = 12,
    output_dir: str | Path = "artifacts/local-simulation",
) -> dict[str, Any]:
    """Run fixture-driven pipeline checks and save clearly labelled artifacts."""
    if agent not in {"knowledge", "workflow", "both"}:
        raise ValueError("agent must be knowledge, workflow or both.")
    if split not in {"development", "evaluation", "all"}:
        raise ValueError("split must be development, evaluation or all.")
    if not 1 <= limit <= 12:
        raise ValueError("limit must be between 1 and 12 per agent.")

    agents = {"knowledge", "workflow"} if agent == "both" else {agent}
    cases = [
        case for case in load_dataset()
        if case["agent_type"] in agents
        and (split == "all" or case["split"] == split)
    ]
    selected = []
    for agent_type in sorted(agents):
        selected.extend([
            case for case in cases if case["agent_type"] == agent_type
        ][:limit])
    if not selected:
        raise ValueError("No benchmark scenarios matched this simulation selection.")

    rows: list[dict[str, Any]] = []
    traces: list[dict[str, Any]] = []
    for case in selected:
        run, sandbox, metrics = simulate_case(case)
        rows.append(metrics)
        traces.append({
            "case_id": case["id"],
            "agent_type": case["agent_type"],
            "execution_mode": "deterministic_fixture_simulation",
            "run": run.to_dict(),
            "final_sandbox_state": sandbox.state,
        })

    by_agent = {}
    for agent_type in sorted(agents):
        group = [row for row in rows if row["agent_type"] == agent_type]
        by_agent[agent_type] = {
            "cases": len(group),
            "grader_fixture_passes": sum(int(row["task_success"]) for row in group),
            "grader_fixture_failures": sum(1 for row in group if not row["task_success"]),
        }

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "execution_mode": "deterministic_fixture_simulation",
        "model_used": None,
        "network_requests": 0,
        "api_cost_usd": 0,
        "configuration": {
            "agent": agent,
            "split": split,
            "limit_per_agent": limit,
            "dataset_version": BENCHMARK_VERSION,
            "scenario_count": len(rows),
        },
        "by_agent": by_agent,
        "cases": [
            {
                "case_id": row["case_id"],
                "agent_type": row["agent_type"],
                "grader_fixture_passed": bool(row["task_success"]),
                "status": row["status"],
            }
            for row in rows
        ],
        "interpretation": (
            "Fixture-driven pipeline validation only. The simulation reads benchmark "
            "expected labels to stage deterministic tool calls. It does not query an LLM "
            "and its pass rate is not model performance evidence."
        ),
    }

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "simulation_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (destination / "simulation_traces.json").write_text(
        json.dumps(traces, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    if rows:
        fieldnames = list(dict.fromkeys(key for row in rows for key in row))
        with (destination / "simulation_results.csv").open(
            "w", newline="", encoding="utf-8"
        ) as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    return summary
