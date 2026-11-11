from workflowbench.dataset import BENCHMARK_VERSION
from workflowbench.experiments import run_one_case
from workflowbench.models import AgentRun


def test_experiment_records_model_write_setting_and_dataset_version(monkeypatch):
    def fake_run_live_agent(**kwargs):
        return AgentRun(
            case_id=kwargs["case"]["id"],
            agent_type=kwargs["case"]["agent_type"],
            strategy=kwargs["strategy"],
            status="completed",
            final_output="Answer",
        )

    monkeypatch.setattr("workflowbench.experiments.run_live_agent", fake_run_live_agent)
    case = {
        "id": "K-metadata",
        "agent_type": "knowledge",
        "task": "Answer from the documents.",
        "expected": {"required_terms": [], "required_doc_ids": [], "must_abstain": False},
    }
    _, metrics = run_one_case(
        case, client=object(), model="gpt-6-luna", strategy="verified",
        allow_writes=True, save=False,
    )

    assert metrics["model"] == "gpt-6-luna"
    assert metrics["allow_writes"] is True
    assert metrics["dataset_version"] == BENCHMARK_VERSION
