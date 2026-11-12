import json
from types import SimpleNamespace

from workflowbench.gemini_agent import run_gemini_agent
from workflowbench.tools import Sandbox


def _tool_call(call_id, name, arguments):
    return SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(name=name, arguments=json.dumps(arguments)),
    )


class FakeChatCompletions:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        usage = SimpleNamespace(prompt_tokens=10, completion_tokens=4)
        if len(self.calls) == 1:
            message = SimpleNamespace(
                content=None,
                tool_calls=[
                    _tool_call(
                        "call-search",
                        "search_documents",
                        {"query": "Access and Identity Standard", "limit": 5},
                    )
                ],
            )
            return SimpleNamespace(
                choices=[SimpleNamespace(message=message, finish_reason="tool_calls")],
                usage=usage,
            )
        if len(self.calls) == 2:
            message = SimpleNamespace(
                content=None,
                tool_calls=[
                    _tool_call(
                        "call-document",
                        "get_document",
                        {"document_id": "DOC-001"},
                    )
                ],
            )
            return SimpleNamespace(
                choices=[SimpleNamespace(message=message, finish_reason="tool_calls")],
                usage=usage,
            )
        message = SimpleNamespace(
            content=(
                "Manager approval is required within one business day. [DOC-001]"
            ),
            tool_calls=None,
        )
        return SimpleNamespace(
            choices=[SimpleNamespace(message=message, finish_reason="stop")],
            usage=usage,
        )


def test_gemini_chat_completion_loop_calls_tools_and_returns_final_answer():
    completions = FakeChatCompletions()
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=completions)
    )
    case = {
        "id": "K-gemini",
        "agent_type": "knowledge",
        "task": "What is the access approval process?",
    }

    run = run_gemini_agent(
        case, Sandbox(), client, "gemini-test-model", strategy="verified"
    )

    assert run.status == "completed"
    assert "[DOC-001]" in run.final_output
    assert len(completions.calls) == 3
    assert run.input_tokens == 30
    assert run.output_tokens == 12
    assert [event.tool_name for event in run.trace if event.event_type == "tool_call"] == [
        "search_documents",
        "get_document",
    ]

    sent_tools = completions.calls[0]["tools"]
    assert sent_tools[0]["type"] == "function"
    assert "function" in sent_tools[0]
    assert sent_tools[0]["function"]["name"] == "get_document" or (
        sent_tools[1]["function"]["name"] == "get_document"
    )
    assert any(message["role"] == "tool" for message in completions.calls[1]["messages"])


def test_gemini_truncated_chat_response_is_not_marked_completed():
    class TruncatedCompletions:
        def create(self, **kwargs):
            message = SimpleNamespace(content="Partial answer", tool_calls=None)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=message, finish_reason="length")],
                usage=SimpleNamespace(prompt_tokens=5, completion_tokens=3),
            )

    client = SimpleNamespace(
        chat=SimpleNamespace(completions=TruncatedCompletions())
    )
    case = {"id": "K-truncated", "agent_type": "knowledge", "task": "Find a fact."}

    run = run_gemini_agent(case, Sandbox(), client, "gemini-test-model")

    assert run.status == "error"
    assert "truncated" in run.error
    assert run.final_output == ""
