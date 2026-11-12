import json
from pathlib import Path

import pytest

from workflowbench.dataset import BENCHMARK_VERSION, load_dataset


def test_benchmark_has_two_agents_and_balanced_tracks():
    cases = load_dataset()
    assert len(cases) == 24
    assert sum(c["agent_type"] == "knowledge" for c in cases) == 12
    assert sum(c["agent_type"] == "workflow" for c in cases) == 12
    assert sum(c["split"] == "development" for c in cases) == 8
    assert sum(c["split"] == "evaluation" for c in cases) == 16
    assert BENCHMARK_VERSION == "starter-v0.2"


def test_every_case_has_an_expected_outcome():
    for case in load_dataset():
        assert case["task"].strip()
        assert isinstance(case["expected"], dict)


def test_knowledge_expected_terms_are_present_in_the_referenced_sources():
    root = Path(__file__).resolve().parents[1]
    documents = json.loads((root / "data" / "documents.json").read_text(encoding="utf-8"))
    document_text = {doc["id"]: doc["content"].casefold() for doc in documents}

    for case in load_dataset():
        if case["agent_type"] != "knowledge":
            continue
        required_ids = case["expected"].get("required_doc_ids", [])
        assert required_ids, f"{case['id']} has no required source IDs"
        assert set(required_ids).issubset(document_text), case["id"]
        source_text = " ".join(document_text[doc_id] for doc_id in required_ids)
        for term in case["expected"].get("required_terms", []):
            assert term.casefold() in source_text, (
                f"{case['id']} expected term {term!r} is not grounded in its source"
            )


def test_loader_rejects_duplicate_ids_and_non_object_cases(tmp_path):
    duplicate_file = tmp_path / "duplicates.jsonl"
    duplicate_file.write_text(
        '{"id":"K1","agent_type":"knowledge","split":"development","task":"A","expected":{}}\n'
        '{"id":"K1","agent_type":"knowledge","split":"development","task":"B","expected":{}}\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Duplicate case ID"):
        load_dataset(duplicate_file)

    non_object_file = tmp_path / "non-object.jsonl"
    non_object_file.write_text('[]\n', encoding="utf-8")
    with pytest.raises(ValueError, match="JSON object"):
        load_dataset(non_object_file)
