import pytest

from workflowbench.cli import _select_benchmark_cases


def test_cli_can_select_one_exact_case_without_running_prior_cases():
    selected = _select_benchmark_cases(
        agent="knowledge",
        split="development",
        limit=4,
        case_id="K02",
    )

    assert len(selected) == 1
    assert selected[0]["id"] == "K02"


def test_cli_rejects_case_id_from_another_agent_or_split():
    with pytest.raises(ValueError, match="K05"):
        _select_benchmark_cases(
            agent="knowledge",
            split="development",
            limit=4,
            case_id="K05",
        )
