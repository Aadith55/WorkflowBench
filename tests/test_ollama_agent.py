import json
from types import SimpleNamespace

from workflowbench.ollama_agent import run_ollama_agent
from workflowbench.tools import Sandbox


def _call(call_id, name, arguments):
    return SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(name=name, arguments=json.dumps(arguments)),
    )


class FakeCompletions:
    def __init__(self):
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        usage = SimpleNamespace(prompt_tokens=8, completion_tokens=5)
        if len(self.requests) == 1:
            message = SimpleNamespace(
                content=None,
                tool_calls=[
                    _call(
                        "search-1",
                        "search_documents",
                        {"query": "Access and Identity Standard", "limit": 5},
                    )
                ],
            )
            return SimpleNamespace(
                choices=[SimpleNamespace(message=message, finish_reason="tool_calls")],
                usage=usage,
            )
        if len(self.requests) == 2:
            message = SimpleNamespace(
                content=None,
                tool_calls=[_call("document-1", "get_document", {"document_id": "DOC-001"})],
            )
            return SimpleNamespace(
                choices=[SimpleNamespace(message=message, finish_reason="tool_calls")],
                usage=usage,
            )
        message = SimpleNamespace(
            content="The requester's manager must approve standard access. [DOC-001]",
            tool_calls=None,
        )
        return SimpleNamespace(
            choices=[SimpleNamespace(message=message, finish_reason="stop")],
            usage=usage,
        )


def test_ollama_runner_uses_local_chat_tool_loop_without_tool_choice_parameter():
    completions = FakeCompletions()
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
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
    assert len(completions.requests) == 3
    assert all("tool_choice" not in request for request in completions.requests)
    assert run.input_tokens == 24
    assert run.output_tokens == 15
    assert [
        event.tool_name for event in run.trace if event.event_type == "tool_call"
    ] == ["search_documents", "get_document"]
