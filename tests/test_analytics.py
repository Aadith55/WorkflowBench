from workflowbench.analytics import mcnemar_exact, summarise_runs, wilson_interval

def test_wilson_interval_contains_observed_rate():
    low,high = wilson_interval(7,10)
    assert 0 <= low <= 0.7 <= high <= 1

def test_mcnemar_uses_only_matched_case_ids():
    baseline = [{"case_id":"A","task_success":0},{"case_id":"B","task_success":1},{"case_id":"C","task_success":0}]
    verified = [{"case_id":"A","task_success":1},{"case_id":"B","task_success":1},{"case_id":"C","task_success":0},{"case_id":"D","task_success":1}]
    result = mcnemar_exact(baseline,verified)
    assert result["matched_cases"] == 3
    assert result["baseline_only_failures"] == 1
    assert result["verified_only_failures"] == 0
    assert 0 <= result["exact_two_sided_p"] <= 1

def test_unknown_cost_remains_unknown():
    result = summarise_runs([{"task_success":1,"latency_ms":100,"estimated_cost_usd":None}])
    assert result["success_rate"] == 1
    assert result["cost_per_success_usd"] is None


def test_cost_per_success_uses_only_successful_runs_with_known_cost():
    result = summarise_runs([
        {"task_success": 1, "latency_ms": 100, "estimated_cost_usd": 0.01},
        {"task_success": 1, "latency_ms": 120, "estimated_cost_usd": None},
        {"task_success": 0, "latency_ms": 140, "estimated_cost_usd": 0.02},
    ])
    assert result["known_cost_successes"] == 1
    assert result["cost_per_success_usd"] == 0.01


def test_wilson_interval_rejects_invalid_counts():
    import pytest
    with pytest.raises(ValueError, match="between zero and total"):
        wilson_interval(11, 10)
