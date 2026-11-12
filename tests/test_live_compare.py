import csv

from workflowbench.live_compare import build_comparison_summary, _write_results_csv


def _row(agent, strategy, pair_id, success, cost):
    return {
        "agent_type": agent,
        "strategy": strategy,
        "pair_id": pair_id,
        "metrics": {
            "case_id": pair_id.split(":")[0],
            "task_success": success,
            "latency_ms": 100,
            "estimated_cost_usd": cost,
        },
    }


def test_comparison_pairs_only_matched_repetitions_and_separates_agents():
    rows = [
        _row("knowledge", "baseline", "K01:repeat-1", 0, 0.01),
        _row("knowledge", "verified", "K01:repeat-1", 1, 0.02),
        _row("knowledge", "baseline", "K02:repeat-1", 1, 0.01),
        _row("knowledge", "verified", "K02:repeat-1", 1, 0.02),
        _row("workflow", "baseline", "W01:repeat-1", 1, 0.03),
        _row("workflow", "verified", "W01:repeat-1", 1, 0.04),
    ]
    summary = build_comparison_summary(rows)

    knowledge = summary["knowledge"]
    assert knowledge["by_strategy"]["baseline"]["n"] == 2
    assert knowledge["by_strategy"]["verified"]["n"] == 2
    assert knowledge["paired_comparison"]["matched_cases"] == 2
    assert knowledge["paired_comparison"]["baseline_only_failures"] == 1
    assert knowledge["paired_comparison"]["verified_only_failures"] == 0
    assert summary["workflow"]["paired_comparison"]["matched_cases"] == 1


def test_comparison_returns_empty_stats_for_missing_strategy():
    rows = [_row("knowledge", "baseline", "K01:repeat-1", 1, None)]
    summary = build_comparison_summary(rows)

    assert summary["knowledge"]["by_strategy"]["baseline"]["n"] == 1
    assert summary["knowledge"]["by_strategy"]["verified"]["n"] == 0
    assert summary["knowledge"]["paired_comparison"]["matched_cases"] == 0



def test_results_csv_includes_metric_columns_from_all_agent_types(tmp_path):
    rows = [
        {
            "agent_type": "knowledge",
            "strategy": "baseline",
            "task_success": 1,
            "required_term_coverage": 1.0,
        },
        {
            "agent_type": "workflow",
            "strategy": "baseline",
            "task_success": 0,
            "state_match_rate": 0.5,
            "sandbox_mutations": 2,
            "mutation_count_match": 0,
            "blocked_action_attempts": 1,
            "tool_errors": 1,
        },
    ]
    destination = tmp_path / "results.csv"

    _write_results_csv(destination, rows)

    with destination.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        exported = list(reader)
        assert {
            "state_match_rate",
            "sandbox_mutations",
            "mutation_count_match",
            "blocked_action_attempts",
            "tool_errors",
        }.issubset(reader.fieldnames)

    assert len(exported) == 2
    assert exported[0]["state_match_rate"] == ""
    assert exported[0]["required_term_coverage"] == "1.0"
    assert exported[1]["required_term_coverage"] == ""



def test_workflow_comparison_requires_explicit_sandbox_write_approval(tmp_path):
    import pytest

    from workflowbench.live_compare import run_comparison

    with pytest.raises(ValueError, match="allow_workflow_writes=True"):
        run_comparison(
            model="local-test-model",
            agent="both",
            split="development",
            cases_per_agent=2,
            repetitions=1,
            output_dir=tmp_path,
            provider="ollama",
        )
