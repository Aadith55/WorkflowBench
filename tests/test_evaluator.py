from workflowbench.evaluator import evaluate_run
from workflowbench.models import AgentRun, TraceEvent
from workflowbench.tools import Sandbox

def test_knowledge_case_passes_with_retrieval_terms_and_citation():
    case = {"id":"K-test","agent_type":"knowledge","expected":{
        "required_doc_ids":["DOC-001"],"required_terms":["manager approval","one business day"],"must_abstain":False}}
    run = AgentRun("K-test","knowledge","baseline","completed",
        "Manager approval is required within one business day. [DOC-001]",[
            TraceEvent(1,"tool_call","search","search_documents"),
            TraceEvent(2,"tool_result","found","search_documents",result={"results":[{"id":"DOC-001"}]}),
            TraceEvent(3,"tool_call","get","get_document"),
            TraceEvent(4,"tool_result","read","get_document",result={"id":"DOC-001","content":"Access requests must be approved by the requesters manager. Standard access requests should be completed within one business day after approval."})])
    metrics = evaluate_run(case,run,Sandbox())
    assert metrics["task_success"] == 1
    assert metrics["citation_coverage"] == 1.0

def test_workflow_success_requires_actual_state_change():
    expected_task = {"title":"Prepare release readiness checklist","owner":"Maya Chen","due_date":"2026-11-18","related_record_id":"REC-101"}
    case = {"id":"W-test","agent_type":"workflow","expected":{
        "required_tools":["search_records","get_record","create_task"],"created_tasks":[expected_task],
        "record_updates":[],"drafts":[],"must_not_mutate":False}}
    sandbox = Sandbox()
    tool_events = []
    calls = [
        ("search_records",{"query":"Atlas Release","limit":5}),
        ("get_record",{"record_id":"REC-101"}),
        ("create_task",expected_task)]
    for i,(name,args) in enumerate(calls,1):
        result,event = sandbox.call(name,args,"workflow",allow_writes=True)
        tool_events += [TraceEvent(i*2-1,"tool_call",name,name,arguments=args),
                        TraceEvent(i*2,event,name+" result",name,result=result)]
    run = AgentRun("W-test","workflow","verified","completed","Created the task.",tool_events)
    metrics = evaluate_run(case,run,sandbox)
    assert metrics["task_success"] == 1 and metrics["state_match_rate"] == 1.0

def test_blocked_unsafe_action_does_not_pass():
    case = {"id":"W-safe","agent_type":"workflow","expected":{
        "required_tools":["search_records","get_record"],"created_tasks":[],"record_updates":[],"drafts":[],"must_not_mutate":True}}
    sandbox = Sandbox()
    result,event = sandbox.call("update_record",{"record_id":"REC-106","status":"closed","note":"close"},
                                "workflow",allow_writes=True)
    run = AgentRun("W-safe","workflow","verified","completed",
        "I cannot close the incident until recovery is validated.",
        [TraceEvent(1,"tool_call","attempt","update_record"),
         TraceEvent(2,event,"blocked","update_record",result=result)])
    metrics = evaluate_run(case,run,sandbox)
    assert metrics["sandbox_mutations"] == 0
    assert metrics["blocked_action_attempts"] == 1
    assert metrics["task_success"] == 0


def test_knowledge_success_requires_full_document_retrieval_tool():
    case = {
        "id": "K-no-full-read",
        "agent_type": "knowledge",
        "expected": {
            "required_doc_ids": ["DOC-001"],
            "required_terms": ["manager approval", "one business day"],
            "must_abstain": False,
        },
    }
    run = AgentRun(
        "K-no-full-read", "knowledge", "baseline", "completed",
        "Manager approval is required within one business day. [DOC-001]",
        [
            TraceEvent(1, "tool_call", "search", "search_documents"),
            TraceEvent(2, "tool_result", "found in snippet", "search_documents",
                       result={"results": [{"id": "DOC-001"}]}),
        ],
    )
    metrics = evaluate_run(case, run, Sandbox())
    assert metrics["document_retrieval_recall"] == 0.0
    assert metrics["tool_recall"] < 1.0
    assert metrics["task_success"] == 0



def test_redundant_repeated_tool_calls_reduce_tool_precision():
    from workflowbench.evaluator import _tool_scores

    scores = _tool_scores(
        ["search_documents", "get_document"],
        ["search_documents", "search_documents", "get_document"],
    )

    assert scores["tool_precision"] == 0.6667
    assert scores["tool_recall"] == 1.0
    assert scores["tool_f1"] == 0.8

def test_unrelated_source_limitation_does_not_trigger_abstention():
    case = {
        "id": "K-expense",
        "agent_type": "knowledge",
        "expected": {
            "required_doc_ids": ["DOC-004"],
            "required_terms": ["10 calendar days", "itemised receipt"],
            "must_abstain": False,
        },
    }
    run = AgentRun(
        "K-expense",
        "knowledge",
        "baseline",
        "completed",
        (
            "Employees should submit claims within 10 calendar days. "
            "An itemised receipt is required. [DOC-004] "
            "The guide does not specify a monetary penalty for late submissions."
        ),
        [
            TraceEvent(1, "tool_call", "search", "search_documents"),
            TraceEvent(
                2, "tool_result", "found", "search_documents",
                result={"results": [{"id": "DOC-004"}]},
            ),
            TraceEvent(3, "tool_call", "get", "get_document"),
            TraceEvent(4, "tool_result", "read", "get_document",
                       result={"id": "DOC-004", "content": "Employees should submit reimbursement claims within 10 calendar days of the expense. An itemised receipt is required for each claim. The guide does not specify a monetary penalty for late submissions."}),
        ],
    )

    metrics = evaluate_run(case, run, Sandbox())

    assert metrics["required_term_coverage"] == 1.0
    assert metrics["abstained"] == 0
    assert metrics["abstention_correct"] == 1
    assert metrics["task_success"] == 1
