from workflowbench.live_compare import build_comparison_summary


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
