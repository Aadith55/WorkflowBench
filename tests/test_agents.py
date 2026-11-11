import json
from types import SimpleNamespace
from workflowbench.agents import run_live_agent
from workflowbench.tools import Sandbox

class FakeResponses:
    def __init__(self): self.calls = 0
    def create(self, **kwargs):
        self.calls += 1
        usage = SimpleNamespace(input_tokens=12,output_tokens=8)
        if self.calls == 1:
            output = [SimpleNamespace(type="function_call",name="search_documents",
                arguments=json.dumps({"query":"access manager approval","limit":5}),call_id="call-1")]
            return SimpleNamespace(output=output,output_text="",usage=usage)
        if self.calls == 2:
            output = [SimpleNamespace(type="function_call",name="get_document",
                arguments=json.dumps({"document_id":"DOC-001"}),call_id="call-2")]
            return SimpleNamespace(output=output,output_text="",usage=usage)
        return SimpleNamespace(output=[SimpleNamespace(type="message")],
            output_text="Manager approval is required within one business day. [DOC-001]",usage=usage)

class FakeClient:
    def __init__(self): self.responses = FakeResponses()

def test_responses_tool_loop_calls_tools_then_returns_final_answer():
    case = {"id":"K-fake","agent_type":"knowledge","task":"What is the access approval process?"}
    client = FakeClient()
    run = run_live_agent(case,Sandbox(),client,"fake-model",strategy="verified")
    assert run.status == "completed"
    assert "[DOC-001]" in run.final_output
    assert client.responses.calls == 3
    assert run.input_tokens == 36
    assert sum(e.event_type == "tool_call" for e in run.trace) == 2
