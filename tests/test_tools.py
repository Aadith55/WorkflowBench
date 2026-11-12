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


def test_unknown_agent_type_fails_closed():
    sandbox = Sandbox()
    result, event = sandbox.call("search_records", {"query": "Atlas", "limit": 5}, "unknown-agent")
    assert event == "tool_denied"
    assert result["ok"] is False


def test_strict_validation_rejects_coercible_types_and_empty_record_links():
    sandbox = Sandbox()
    result, event = sandbox.call(
        "search_documents", {"query": "access request", "limit": "5"}, "knowledge"
    )
    assert event == "tool_error"
    assert result["ok"] is False

    result, event = sandbox.call(
        "create_task",
        {
            "title": "Task without a record",
            "owner": "Maya Chen",
            "due_date": "2026-11-18",
            "related_record_id": "",
        },
        "workflow",
        allow_writes=True,
    )
    assert event == "tool_error"
    assert result["ok"] is False
    assert sandbox.state["tasks"] == []


def test_tool_schemas_reject_unknown_agent_type():
    import pytest
    with pytest.raises(ValueError, match="Unknown agent type"):
        tool_schemas("admin")


def test_strict_json_schemas_use_supported_constraints_only():
    for tool in tool_schemas("knowledge") + tool_schemas("workflow"):
        properties = tool["parameters"]["properties"]
        for schema in properties.values():
            assert "minLength" not in schema
            assert "maxLength" not in schema
        assert tool["strict"] is True
        assert tool["parameters"]["additionalProperties"] is False
        assert set(tool["parameters"]["required"]) == set(properties)
    create_task = next(
        tool for tool in tool_schemas("workflow") if tool["name"] == "create_task"
    )
    assert create_task["parameters"]["properties"]["due_date"]["pattern"] == r"^\d{4}-\d{2}-\d{2}$"

def test_get_document_schema_explains_exact_document_id_argument():
    schema = next(tool for tool in tool_schemas("knowledge") if tool["name"] == "get_document")
    assert set(schema["parameters"]["properties"]) == {"document_id"}
    assert "exact document ID" in schema["description"]
    assert "do not pass the search query or limit" in schema["description"]
    assert "Exact source ID" in schema["parameters"]["properties"]["document_id"]["description"]


def test_invalid_get_document_arguments_return_actionable_validation_details():
    sandbox = Sandbox()
    result, event = sandbox.call(
        "get_document",
        {"query": "account disable worker departure", "limit": 1},
        "knowledge",
    )

    assert event == "tool_error"
    assert result["ok"] is False
    locations = {detail["location"] for detail in result["details"]}
    assert "document_id" in locations
    assert "query" in locations
    assert "limit" in locations
    assert sandbox.mutations == 0
