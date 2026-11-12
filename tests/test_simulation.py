import csv
import json

from workflowbench.dataset import load_dataset
from workflowbench.simulation import run_local_simulation, simulate_case


def test_all_scenarios_pass_fixture_pipeline_without_model_or_network_calls(tmp_path):
    summary = run_local_simulation(
        agent="both",
        split="all",
        limit=12,
        output_dir=tmp_path,
    )

    assert summary["execution_mode"] == "deterministic_fixture_simulation"
    assert summary["model_used"] is None
    assert summary["network_requests"] == 0
    assert summary["api_cost_usd"] == 0
    assert summary["configuration"]["scenario_count"] == 24
    failed_cases = [
        item["case_id"] for item in summary["cases"]
        if not item["grader_fixture_passed"]
    ]
    assert not failed_cases, f"Fixture cases failed deterministic grading: {failed_cases}"

    assert (tmp_path / "simulation_summary.json").exists()
    assert (tmp_path / "simulation_traces.json").exists()
    with (tmp_path / "simulation_results.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 24
    assert {row["execution_mode"] for row in rows} == {
        "deterministic_fixture_simulation"
    }
    saved_summary = json.loads(
        (tmp_path / "simulation_summary.json").read_text(encoding="utf-8")
    )
    assert "not model performance evidence" in saved_summary["interpretation"]


def test_safety_scenarios_do_not_mutate_workspace():
    cases = {case["id"]: case for case in load_dataset()}
    for case_id in ("W08", "W11"):
        run, sandbox, metrics = simulate_case(cases[case_id])
        assert run.status == "completed"
        assert sandbox.mutations == 0
        assert metrics["sandbox_mutations"] == 0
        assert metrics["task_success"] == 1


def test_abstention_case_is_explicitly_marked_as_not_specified():
    cases = {case["id"]: case for case in load_dataset()}
    run, _, metrics = simulate_case(cases["K12"])
    assert run.status == "completed"
    assert "not specified" in run.final_output.lower()
    assert "[DOC-004]" in run.final_output
    assert metrics["task_success"] == 1
