"""Fixed walkthroughs for learning; these are not model outputs or benchmark results."""
from .models import AgentRun, TraceEvent
from .tools import Sandbox

def _call(sandbox, trace, name, args, agent, allow_writes=False):
    result, event = sandbox.call(name, args, agent, allow_writes)
    trace.append(TraceEvent(len(trace)+1, "tool_call", f"Demo requested {name}.", name, args))
    trace.append(TraceEvent(len(trace)+1, event, f"{name} returned {event}.", name, result=result))
    return result

def run_scripted_walkthrough(agent_type: str):
    sandbox, trace = Sandbox(), []
    if agent_type == "knowledge":
        result = _call(sandbox, trace, "search_documents", {"query":"access request manager approval standard","limit":5}, agent_type)
        doc_id = next(x["id"] for x in result["results"] if x["id"] == "DOC-001")
        _call(sandbox, trace, "get_document", {"document_id":doc_id}, agent_type)
        answer = "A standard access request must be approved by the requester's manager and completed within one business day. [DOC-001]"
        case_id = "DEMO-KNOWLEDGE"
    else:
        result = _call(sandbox, trace, "search_records", {"query":"Atlas Release","limit":5}, agent_type)
        record = next(x for x in result["results"] if x["id"] == "REC-101")
        _call(sandbox, trace, "get_record", {"record_id":record["id"]}, agent_type)
        result = _call(sandbox, trace, "create_task", {"title":"Prepare release readiness checklist","owner":"Maya Chen","due_date":"2026-11-18","related_record_id":"REC-101"}, agent_type, True)
        answer = f"Created sandbox task {result['task']['id']} for Maya Chen. No notification was sent."
        case_id = "DEMO-WORKFLOW"
    trace.append(TraceEvent(len(trace)+1, "final", "Scripted walkthrough complete.", result=answer))
    return AgentRun(case_id, agent_type, "scripted_walkthrough", "demo_only", answer, trace), sandbox.state
