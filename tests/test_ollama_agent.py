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
        and "Call get_document" in message.get("content", "")
        for message in sent_payloads[2]["messages"]
    )
    assert run.final_output.startswith("The requester's manager")
    assert "analysis" not in run.final_output.lower()
