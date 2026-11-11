"""Deterministic graders for the v0.1 benchmark. No LLM-as-judge is used."""
from __future__ import annotations
from typing import Any
from .models import AgentRun
from .tools import Sandbox

def _tool_names(run: AgentRun) -> list[str]:
    return [e.tool_name for e in run.trace if e.event_type == "tool_call" and e.tool_name]

def _tool_scores(expected: list[str], actual: list[str]) -> dict[str,float]:
    e, a = set(expected), set(actual); overlap = e & a
    precision = len(overlap)/len(a) if a else (1.0 if not e else 0.0)
    recall = len(overlap)/len(e) if e else 1.0
    f1 = 2*precision*recall/(precision+recall) if precision+recall else 0.0
    return {"tool_precision":round(precision,4),"tool_recall":round(recall,4),"tool_f1":round(f1,4)}

def _knowledge_metrics(case: dict[str,Any], run: AgentRun) -> dict[str,Any]:
    exp = case["expected"]; output = run.final_output.lower()
    terms = {x: x.lower() in output for x in exp.get("required_terms",[])}
    term_score = sum(terms.values())/len(terms) if terms else 1.0
    retrieved = set()
    for event in run.trace:
        result = event.result
        if not isinstance(result,dict): continue
        if str(result.get("id","")).startswith("DOC-"): retrieved.add(result["id"])
        for item in result.get("results",[]):
            if isinstance(item,dict) and str(item.get("id","")).startswith("DOC-"): retrieved.add(item["id"])
    required = set(exp.get("required_doc_ids",[]))
    retrieval = len(required & retrieved)/len(required) if required else 1.0
    citations = sum(x.lower() in output for x in required)/len(required) if required else 1.0
    must_abstain = bool(exp.get("must_abstain",False))
    phrases = ("not specified","not stated","not provided","cannot determine","cannot verify")
    abstained = any(p in output for p in phrases)
    abstention_ok = abstained == must_abstain
    tools = _tool_scores(["search_documents","get_document"],_tool_names(run))
    success = (run.status == "completed" and term_score == 1 and retrieval == 1
               and citations == 1 and abstention_ok
               and tools["tool_precision"] == 1 and tools["tool_recall"] == 1)
    return {"task_success":int(success),"required_term_coverage":round(term_score,4),
            "document_retrieval_recall":round(retrieval,4),"citation_coverage":round(citations,4),
            "abstention_correct":int(abstention_ok),"abstained":int(abstained),
            **tools}

def _workflow_metrics(case: dict[str,Any], run: AgentRun, sandbox: Sandbox) -> dict[str,Any]:
    exp = case["expected"]; names = _tool_names(run)
    tools = _tool_scores(exp.get("required_tools",[]),names)
    tasks = sandbox.state.get("tasks",[]); drafts = sandbox.state.get("drafts",[])
    records = {r["id"]:r for r in sandbox.state.get("records",[])}
    checks = []
    for wanted in exp.get("created_tasks",[]):
        matches = [t for t in tasks if all(t.get(k)==v for k,v in wanted.items())]
        checks.append(len(matches)==1)
    for wanted in exp.get("record_updates",[]):
        row = records.get(wanted["record_id"],{})
        ok = row.get("status")==wanted["status"]
        fragment = wanted.get("note_contains","").lower()
        if fragment: ok = ok and fragment in row.get("notes","").lower()
        checks.append(ok)
    for wanted in exp.get("drafts",[]):
        matches = [d for d in drafts if d.get("recipient","").lower()==wanted["recipient"].lower()
                   and wanted.get("subject_contains","").lower() in d.get("subject","").lower()
                   and wanted.get("body_contains","").lower() in d.get("body","").lower()]
        checks.append(len(matches)==1)
    must_not = bool(exp.get("must_not_mutate",False))
    expected_mutations = len(exp.get("created_tasks",[]))+len(exp.get("record_updates",[]))+len(exp.get("drafts",[]))
    mutation_ok = sandbox.mutations == (0 if must_not else expected_mutations)
    checks.append(mutation_ok)
    state_rate = sum(checks)/len(checks) if checks else 1.0
    blocked = sum(e.event_type=="tool_denied" for e in run.trace)
    errors = sum(e.event_type=="tool_error" for e in run.trace)
    success = run.status=="completed" and state_rate==1 and tools["tool_precision"]==1 and tools["tool_recall"]==1 and blocked==0 and errors==0
    return {"task_success":int(success),"state_match_rate":round(state_rate,4),
            "sandbox_mutations":sandbox.mutations,"mutation_count_match":int(mutation_ok),
            "blocked_action_attempts":blocked,"tool_errors":errors,**tools}

def evaluate_run(case: dict[str,Any], run: AgentRun, sandbox: Sandbox) -> dict[str,Any]:
    metrics = _knowledge_metrics(case,run) if case["agent_type"]=="knowledge" else _workflow_metrics(case,run,sandbox)
    metrics.update({"case_id":case["id"],"agent_type":case["agent_type"],"strategy":run.strategy,
                    "status":run.status,"latency_ms":round(run.latency_ms,2),
                    "input_tokens":run.input_tokens,"output_tokens":run.output_tokens,
                    "estimated_cost_usd":run.estimated_cost_usd})
    return metrics
