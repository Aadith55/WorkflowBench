import json
from types import SimpleNamespace

from workflowbench.ollama_agent import run_ollama_agent
from workflowbench.tools import Sandbox


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.payload


class FakeOllama:
    def __init__(self):
        self.requests = []

    def urlopen(self, request, timeout):
        payload = json.loads(request.data.decode("utf-8"))
        self.requests.append((request.full_url, payload, timeout))
        if len(self.requests) == 1:
            return FakeResponse({
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [{
                        "function": {
                            "name": "search_documents",
                            "arguments": {
                                "query": "Access and Identity Standard",
                                "limit": 5,
                            },
                        },
                    }],
                },
                "done": True,
                "done_reason": "stop",
                "prompt_eval_count": 8,
                "eval_count": 5,
            })
        if len(self.requests) == 2:
            return FakeResponse({
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [{
                        "function": {
                            "name": "get_document",
                            "arguments": {"document_id": "DOC-001"},
                        },
                    }],
                },
                "done": True,
                "done_reason": "stop",
                "prompt_eval_count": 9,
                "eval_count": 4,
            })
        return FakeResponse({
            "message": {
                "role": "assistant",
                "content": "The requester's manager must approve standard access. [DOC-001]",
            },
            "done": True,
            "done_reason": "stop",
            "prompt_eval_count": 10,
            "eval_count": 12,
        })


def test_ollama_runner_uses_native_api_disables_thinking_and_completes_tool_loop(monkeypatch):
    fake = FakeOllama()
    monkeypatch.setattr("workflowbench.ollama_agent.urlopen", fake.urlopen)
    client = SimpleNamespace(base_url="http://localhost:11434/v1/")
    case = {
        "id": "K-ollama",
        "agent_type": "knowledge",
        "task": "Who approves standard access requests?",
    }

    run = run_ollama_agent(
        case, Sandbox(), client, "qwen3:4b", strategy="verified"
    )

    assert run.status == "completed"
    assert "[DOC-001]" in run.final_output
    assert len(fake.requests) == 3
    assert all(url == "http://localhost:11434/api/chat" for url, _, _ in fake.requests)
    assert all(payload["think"] is False for _, payload, _ in fake.requests)
    assert all(payload["stream"] is False for _, payload, _ in fake.requests)
    assert all(payload["options"]["num_predict"] == 2048 for _, payload, _ in fake.requests)
    assert run.input_tokens == 27
    assert run.output_tokens == 21
    assert [
        event.tool_name for event in run.trace if event.event_type == "tool_call"
    ] == ["search_documents", "get_document"]

    second_messages = fake.requests[1][1]["messages"]
    assert second_messages[-2]["role"] == "assistant"
    assert second_messages[-1]["role"] == "tool"
    assert second_messages[-1]["tool_name"] == "search_documents"


def test_ollama_runner_reports_output_limit_errors_with_usage(monkeypatch):
    fake = FakeResponse({
        "message": {"role": "assistant", "content": ""},
        "done": True,
        "done_reason": "length",
        "prompt_eval_count": 100,
        "eval_count": 2048,
    })
    monkeypatch.setattr("workflowbench.ollama_agent.urlopen", lambda *_args, **_kwargs: fake)
    client = SimpleNamespace(base_url="http://localhost:11434/v1/")
    case = {
        "id": "K-truncated",
        "agent_type": "knowledge",
        "task": "Who approves standard access requests?",
    }

    run = run_ollama_agent(case, Sandbox(), client, "qwen3:4b")

    assert run.status == "error"
    assert "2048-token output limit" in run.error
    assert run.input_tokens == 100
    assert run.output_tokens == 2048

def test_ollama_runner_blocks_knowledge_final_until_full_document_is_retrieved(monkeypatch):
    responses = [
        {
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "function": {
                        "name": "search_documents",
                        "arguments": {"query": "Access and Identity Standard", "limit": 5},
                    },
                }],
            },
            "done": True,
            "done_reason": "stop",
            "prompt_eval_count": 10,
            "eval_count": 8,
        },
        {
            "message": {
                "role": "assistant",
                "content": "The requester's manager approves the request. [DOC-001]",
            },
            "done": True,
            "done_reason": "stop",
            "prompt_eval_count": 30,
            "eval_count": 14,
        },
        {
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "function": {
                        "name": "get_document",
                        "arguments": {"document_id": "DOC-001"},
                    },
                }],
            },
            "done": True,
            "done_reason": "stop",
            "prompt_eval_count": 40,
            "eval_count": 9,
        },
        {
            "message": {
                "role": "assistant",
                "content": (
                    "The requester's manager approves a standard access request, "
                    "which should be completed within one business day. [DOC-001]"
                ),
            },
            "done": True,
            "done_reason": "stop",
            "prompt_eval_count": 50,
            "eval_count": 18,
        },
    ]

    def fake_urlopen(request, timeout):
        payload = json.loads(request.data.decode("utf-8"))
        sent_payloads.append(payload)
        return FakeResponse(responses.pop(0))

    sent_payloads = []
    monkeypatch.setattr("workflowbench.ollama_agent.urlopen", fake_urlopen)
    client = SimpleNamespace(base_url="http://localhost:11434/v1/")
    case = {
        "id": "K-gated",
        "agent_type": "knowledge",
        "task": "Who approves standard access requests and how quickly should it be completed?",
    }
    sandbox = Sandbox()
    run = run_ollama_agent(case, sandbox, client, "qwen3:4b")

    assert run.status == "completed"
    assert len(sent_payloads) == 4
    assert "get_document" in [
        event.tool_name for event in run.trace if event.event_type == "tool_call"
    ]
    assert any(event.event_type == "retrieval_gate" for event in run.trace)
    assert any(
        message.get("role") == "user"
        and "call get_document" in message.get("content", "").lower()
        for message in sent_payloads[2]["messages"]
    )
    assert run.final_output.startswith("The requester's manager")
    assert "analysis" not in run.final_output.lower()

def test_ollama_runner_requests_citation_before_accepting_knowledge_answer(monkeypatch):
    responses = [
        {
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "function": {
                        "name": "search_documents",
                        "arguments": {"query": "access standard", "limit": 5},
                    },
                }],
            },
            "done": True,
            "done_reason": "stop",
            "prompt_eval_count": 10,
            "eval_count": 8,
        },
        {
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "function": {
                        "name": "get_document",
                        "arguments": {"document_id": "DOC-001"},
                    },
                }],
            },
            "done": True,
            "done_reason": "stop",
            "prompt_eval_count": 30,
            "eval_count": 9,
        },
        {
            "message": {
                "role": "assistant",
                "content": (
                    "The requester's manager approves the access request. "
                    "It should be completed within one business day after approval."
                ),
            },
            "done": True,
            "done_reason": "stop",
            "prompt_eval_count": 40,
            "eval_count": 20,
        },
        {
            "message": {
                "role": "assistant",
                "content": (
                    "The requester's manager must approve a standard access request, "
                    "which should be completed within one business day after approval. "
                    "[DOC-001]"
                ),
            },
            "done": True,
            "done_reason": "stop",
            "prompt_eval_count": 55,
            "eval_count": 25,
        },
    ]

    sent_payloads = []

    def fake_urlopen(request, timeout):
        sent_payloads.append(json.loads(request.data.decode("utf-8")))
        return FakeResponse(responses.pop(0))

    monkeypatch.setattr("workflowbench.ollama_agent.urlopen", fake_urlopen)
    client = SimpleNamespace(base_url="http://localhost:11434/v1/")
    case = {
        "id": "K-citation",
        "agent_type": "knowledge",
        "task": "Who approves a standard access request and when should it be completed?",
        "expected": {"required_doc_ids": ["DOC-001"]},
    }

    run = run_ollama_agent(case, Sandbox(), client, "qwen3:1.7b")

    assert run.status == "completed"
    assert len(sent_payloads) == 4
    assert "[DOC-001]" in run.final_output
    assert any(event.event_type == "citation_gate" for event in run.trace)
    correction = sent_payloads[3]["messages"][-1]["content"]
    assert "[DOC-001]" in correction
    assert "do not change what a deadline applies to" in correction
    assert "within one business day after approval" in correction



def _ollama_payload(tool_name=None, arguments=None, content=""):
    message = {"role": "assistant", "content": content}
    if tool_name:
        message["tool_calls"] = [{
            "function": {"name": tool_name, "arguments": arguments or {}},
        }]
    return {
        "message": message,
        "done": True,
        "done_reason": "stop",
        "prompt_eval_count": 12,
        "eval_count": 8,
    }


def test_ollama_rejects_document_id_not_returned_by_search_and_accepts_exact_hit(monkeypatch):
    responses = [
        _ollama_payload(
            "search_documents",
            {"query": "Severity 1 incident", "limit": 5},
        ),
        _ollama_payload("get_document", {"document_id": "DOC-001"}),
        _ollama_payload("get_document", {"document_id": "DOC-002"}),
        _ollama_payload(
            content=(
                "The on-call responder must notify the incident commander within "
                "15 minutes of confirmation. Status updates must be recorded every "
                "30 minutes. [DOC-002]"
            )
        ),
    ]
    sent_payloads = []

    def fake_urlopen(request, timeout):
        sent_payloads.append(json.loads(request.data.decode("utf-8")))
        return FakeResponse(responses.pop(0))

    monkeypatch.setattr("workflowbench.ollama_agent.urlopen", fake_urlopen)
    client = SimpleNamespace(base_url="http://localhost:11434/v1/")
    case = {
        "id": "K-wrong-id",
        "agent_type": "knowledge",
        "task": (
            "For a confirmed Severity 1 incident, what is the initial notification "
            "deadline and how often must status updates be recorded?"
        ),
        "expected": {"required_doc_ids": ["DOC-002"]},
    }

    run = run_ollama_agent(case, Sandbox(), client, "qwen3:1.7b", strategy="verified")

    assert run.status == "completed"
    assert run.final_output.endswith("[DOC-002]")
    failed_reads = [
        event for event in run.trace
        if event.event_type == "tool_error" and event.tool_name == "get_document"
    ]
    assert len(failed_reads) == 1
    assert failed_reads[0].result["available_document_ids"] == ["DOC-002"]
    successful_reads = [
        event for event in run.trace
        if event.event_type == "tool_result" and event.tool_name == "get_document"
    ]
    assert [event.result["id"] for event in successful_reads] == ["DOC-002"]

    system_prompt = sent_payloads[0]["messages"][0]["content"]
    schema_text = json.dumps(sent_payloads[0]["tools"])
    assert "DOC-001" not in system_prompt
    assert "DOC-001" not in schema_text
    assert "Do not assume a default ID" in system_prompt


def test_ollama_citation_gate_uses_retrieved_ids_not_benchmark_answer_key(monkeypatch):
    responses = [
        _ollama_payload(
            "search_documents",
            {"query": "Severity 1 incident", "limit": 5},
        ),
        _ollama_payload("get_document", {"document_id": "DOC-002"}),
        _ollama_payload(
            content=(
                "Notify the incident commander within 15 minutes and record status "
                "updates every 30 minutes."
            )
        ),
        _ollama_payload(
            content=(
                "Notify the incident commander within 15 minutes and record status "
                "updates every 30 minutes. [DOC-002]"
            )
        ),
    ]
    sent_payloads = []

    def fake_urlopen(request, timeout):
        sent_payloads.append(json.loads(request.data.decode("utf-8")))
        return FakeResponse(responses.pop(0))

    monkeypatch.setattr("workflowbench.ollama_agent.urlopen", fake_urlopen)
    client = SimpleNamespace(base_url="http://localhost:11434/v1/")
    # Deliberately inconsistent oracle metadata: the runner must not expose it.
    case = {
        "id": "K-no-oracle-leak",
        "agent_type": "knowledge",
        "task": "For a confirmed Severity 1 incident, state the notification and update timings.",
        "expected": {"required_doc_ids": ["DOC-001"]},
    }

    run = run_ollama_agent(case, Sandbox(), client, "qwen3:1.7b", strategy="baseline")

    assert run.status == "completed"
    assert run.final_output.endswith("[DOC-002]")
    gate = next(event for event in run.trace if event.event_type == "citation_gate")
    assert "DOC-002" in gate.message
    assert "DOC-001" not in gate.message
    correction = sent_payloads[3]["messages"][-1]["content"]
    assert "[DOC-002]" in correction
    assert "[DOC-001]" not in correction
    assert "15 minutes" in correction
