from workflowbench.tools import Sandbox, tool_schemas

def test_document_search_and_retrieval():
    sandbox = Sandbox()
    result = sandbox.search_documents("access request manager approval")
    assert result["results"] and result["results"][0]["id"] == "DOC-001"
    assert "one business day" in sandbox.get_document("DOC-001")["content"]

def test_write_tools_are_blocked_without_explicit_permission():
    sandbox = Sandbox()
    result, event = sandbox.call("create_task", {
        "title":"Test task","owner":"Maya Chen","due_date":"2026-11-18","related_record_id":"REC-101"
    }, "workflow", allow_writes=False)
    assert event == "tool_denied" and result["ok"] is False
    assert sandbox.state["tasks"] == [] and sandbox.mutations == 0

def test_incident_cannot_be_closed_before_recovery_validation():
    sandbox = Sandbox()
    result, event = sandbox.call("update_record", {
        "record_id":"REC-106","status":"closed","note":"close"
    }, "workflow", allow_writes=True)
    assert event == "tool_denied" and result["ok"] is False
    assert sandbox.get_record("REC-106")["status"] == "investigating"
    assert sandbox.mutations == 0

def test_message_tool_only_creates_a_draft():
    sandbox = Sandbox()
    result, _ = sandbox.call("draft_message", {
        "recipient":"Maya Chen","subject":"Atlas update","body":"Review is pending."
    }, "workflow", allow_writes=True)
    assert result["ok"] is True and result["sent"] is False
    assert len(sandbox.state["drafts"]) == 1

def test_tool_schemas_are_strict_and_agent_specific():
    knowledge = tool_schemas("knowledge")
    workflow = tool_schemas("workflow")
    assert {x["name"] for x in knowledge} == {"search_documents","get_document"}
    assert "create_task" not in {x["name"] for x in knowledge}
    for tool in knowledge + workflow:
        assert tool["strict"] is True
        assert tool["parameters"]["additionalProperties"] is False
        assert set(tool["parameters"]["required"]) == set(tool["parameters"]["properties"])

def test_pydantic_rejects_invalid_tool_arguments_before_function_runs():
    sandbox = Sandbox()
    result, event = sandbox.call("create_task", {
        "title":"Bad date","owner":"Maya Chen","due_date":"not-a-date","related_record_id":"REC-101"
    }, "workflow", allow_writes=True)
    assert event == "tool_error" and result["ok"] is False
    assert sandbox.state["tasks"] == []
