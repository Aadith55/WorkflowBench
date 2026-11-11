from workflowbench.dataset import load_dataset

def test_benchmark_has_two_agents_and_balanced_tracks():
    cases = load_dataset()
    assert len(cases) == 24
    assert sum(c["agent_type"] == "knowledge" for c in cases) == 12
    assert sum(c["agent_type"] == "workflow" for c in cases) == 12
    assert sum(c["split"] == "development" for c in cases) == 8
    assert sum(c["split"] == "evaluation" for c in cases) == 16

def test_every_case_has_an_expected_outcome():
    for case in load_dataset():
        assert case["task"].strip()
        assert isinstance(case["expected"], dict)
