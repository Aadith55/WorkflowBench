"""Local, sandboxed tools available to the two agents.

All writes stay in an in-memory workspace. No tool sends emails or calls external systems.
"""
from __future__ import annotations
import json
import re
import time
from copy import deepcopy
from pathlib import Path
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from .dataset import DATA_DIR

STOP_WORDS = {"a","an","and","are","as","at","be","before","by","can","do","does","for","from","how","i","in","is","it","must","of","on","or","the","this","to","what","when","who","with","within","should","after","their"}

class ToolArguments(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
class SearchArguments(ToolArguments):
    query: str = Field(min_length=1, max_length=240)
    limit: int = Field(ge=1, le=5)
class GetDocumentArguments(ToolArguments):
    document_id: str = Field(min_length=1, max_length=40)
class GetRecordArguments(ToolArguments):
    record_id: str = Field(min_length=1, max_length=40)
class CreateTaskArguments(ToolArguments):
    title: str = Field(min_length=1, max_length=160)
    owner: str = Field(min_length=1, max_length=100)
    due_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    related_record_id: str = Field(min_length=1, max_length=40)
    @field_validator("due_date")
    @classmethod
    def valid_calendar_date(cls, value: str) -> str:
        from datetime import date
        date.fromisoformat(value)
        return value
class UpdateRecordArguments(ToolArguments):
    record_id: str = Field(min_length=1, max_length=40)
    status: Literal["active","open","in_progress","blocked","done","review","pending_review","investigating","closed"]
    note: str = Field(max_length=1000)
class DraftMessageArguments(ToolArguments):
    recipient: str = Field(min_length=1, max_length=120)
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=3000)

ARGUMENT_MODELS = {
    "search_documents": SearchArguments, "get_document": GetDocumentArguments,
    "search_records": SearchArguments, "get_record": GetRecordArguments,
    "create_task": CreateTaskArguments, "update_record": UpdateRecordArguments,
    "draft_message": DraftMessageArguments,
}
def _tokens(value: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", value.lower()) if w not in STOP_WORDS}

class Sandbox:
    """Disposable copy of sample documents and workspace state."""
    def __init__(self, documents_path: str | Path | None = None, workspace_path: str | Path | None = None):
        docs = Path(documents_path) if documents_path else DATA_DIR / "documents.json"
        workspace = Path(workspace_path) if workspace_path else DATA_DIR / "workspace.json"
        self.documents = json.loads(docs.read_text(encoding="utf-8"))
        self.state = json.loads(workspace.read_text(encoding="utf-8"))
        self.initial_state = deepcopy(self.state)
        self.mutations = 0
    def _search(self, query: str, rows: list[dict[str, Any]], fields: tuple[str, ...], limit: int):
        terms = _tokens(query)
        if not terms: return []
        ranked = []
        for row in rows:
            text = " ".join(str(row.get(field, "")) for field in fields)
            score = len(terms & _tokens(text))
            if score: ranked.append((score, row))
        ranked.sort(key=lambda pair: (-pair[0], str(pair[1].get("id", ""))))
        return [deepcopy(row) for _, row in ranked[:limit]]
    def search_documents(self, query: str, limit: int = 5):
        rows = self._search(query, self.documents, ("title","content","id"), limit)
        return {"results":[{"id":d["id"],"title":d["title"],"version":d["version"],"snippet":d["content"][:260]} for d in rows]}
    def get_document(self, document_id: str):
        for row in self.documents:
            if row["id"] == document_id: return deepcopy(row)
        return {"error": f"Document {document_id} was not found."}
    def search_records(self, query: str, limit: int = 5):
        rows = self._search(query, self.state["records"], ("id","type","name","status","owner","notes"), limit)
        return {"results": rows}
    def get_record(self, record_id: str):
        for row in self.state["records"]:
            if row["id"] == record_id: return deepcopy(row)
        return {"error": f"Record {record_id} was not found."}
    def create_task(self, title: str, owner: str, due_date: str, related_record_id: str):
        if not title.strip() or not owner.strip(): return {"ok":False,"error":"Task title and owner are required."}
        if not related_record_id.strip():
            return {"ok":False,"error":"A related record ID is required."}
        if not any(r["id"] == related_record_id for r in self.state["records"]):
            return {"ok":False,"error":f"Related record {related_record_id} does not exist."}
        task = {"id":f"TASK-{len(self.state['tasks'])+1:03d}","title":title.strip(),"owner":owner.strip(),"due_date":due_date,"related_record_id":related_record_id}
        self.state["tasks"].append(task); self.mutations += 1
        return {"ok":True,"task":deepcopy(task)}
    def update_record(self, record_id: str, status: str, note: str):
        allowed = {"active","open","in_progress","blocked","done","review","pending_review","investigating","closed"}
        if status not in allowed: return {"ok":False,"error":f"Status '{status}' is not allowed."}
        for row in self.state["records"]:
            if row["id"] != record_id: continue
            if row.get("type") == "incident" and status == "closed" and not row.get("recovery_validated",False):
                return {"ok":False,"error":"Cannot close this incident until recovery validation is recorded."}
            row["status"] = status
            if note.strip(): row["notes"] = (row.get("notes","") + " " + note.strip()).strip()
            self.mutations += 1
            return {"ok":True,"record":deepcopy(row)}
        return {"ok":False,"error":f"Record {record_id} was not found."}
    def draft_message(self, recipient: str, subject: str, body: str):
        if not recipient.strip() or not subject.strip() or not body.strip():
            return {"ok":False,"error":"Recipient, subject and body are required."}
        draft = {"recipient":recipient.strip(),"subject":subject.strip(),"body":body.strip()}
        self.state["drafts"].append(draft); self.mutations += 1
        return {"ok":True,"draft":deepcopy(draft),"sent":False}
    def call(self, name: str, arguments: dict[str, Any], agent_type: str, allow_writes: bool = False):
        if agent_type not in {"knowledge","workflow"}:
            return {"ok":False,"error":f"Unknown agent type '{agent_type}'."}, "tool_denied"
        if not isinstance(arguments, dict):
            return {"ok":False,"error":"Tool arguments must be a JSON object."}, "tool_error"
        allowed = KNOWLEDGE_TOOLS if agent_type == "knowledge" else WORKFLOW_TOOLS
        if name not in allowed:
            return {"ok":False,"error":f"Tool '{name}' is not available to this agent."}, "tool_denied"
        if name in WRITE_TOOLS and not allow_writes:
            return {"ok":False,"error":"Sandbox writes are disabled. Ask for approval before retrying."}, "tool_denied"
        functions = {"search_documents":self.search_documents,"get_document":self.get_document,"search_records":self.search_records,"get_record":self.get_record,"create_task":self.create_task,"update_record":self.update_record,"draft_message":self.draft_message}
        try:
            validated = ARGUMENT_MODELS[name].model_validate(arguments)
            result = functions[name](**validated.model_dump())
        except ValidationError as exc:
            # Give the model actionable schema feedback so it can repair a malformed
            # tool call instead of guessing from a generic validation error.
            details = [
                {
                    "location": ".".join(str(part) for part in error.get("loc", ())),
                    "type": str(error.get("type", "validation_error")),
                    "message": str(error.get("msg", "Invalid value.")),
                }
                for error in exc.errors()
            ]
            return {
                "ok": False,
                "error": f"Tool arguments failed validation: {exc.error_count()} issue(s).",
                "details": details,
            }, "tool_error"
        except Exception as exc:
            return {"ok":False,"error":f"Tool failed: {type(exc).__name__}"}, "tool_error"
        if isinstance(result, dict) and result.get("ok") is False:
            if name == "update_record" and "Cannot close this incident" in result.get("error",""):
                return result, "tool_denied"
            return result, "tool_error"
        return result, "tool_result"

KNOWLEDGE_TOOLS = {"search_documents","get_document"}
WORKFLOW_TOOLS = {"search_records","get_record","create_task","update_record","draft_message"}
WRITE_TOOLS = {"create_task","update_record","draft_message"}

def tool_schemas(agent_type: str) -> list[dict[str, Any]]:
    definitions = {
      "search_documents":("Search the local document library.",{"query":{"type":"string"},"limit":{"type":"integer","minimum":1,"maximum":5}},["query","limit"]),
      "get_document":("Retrieve the full source document using the exact document ID returned by search_documents. Pass only document_id (for example DOC-001); do not pass the search query or limit.",{"document_id":{"type":"string","description":"Exact source ID from search_documents results, such as DOC-001. This is not the search query."}},["document_id"]),
      "search_records":("Search local workspace records.",{"query":{"type":"string"},"limit":{"type":"integer","minimum":1,"maximum":5}},["query","limit"]),
      "get_record":("Retrieve one workspace record by ID.",{"record_id":{"type":"string"}},["record_id"]),
      "create_task":("Create a task in the disposable local sandbox; no notification is sent.",{"title":{"type":"string"},"owner":{"type":"string"},"due_date":{"type":"string","pattern":"^\\d{4}-\\d{2}-\\d{2}$","description":"ISO date YYYY-MM-DD"},"related_record_id":{"type":"string","description":"ID of an existing workspace record"}},["title","owner","due_date","related_record_id"]),
      "update_record":("Update status and append a note to a sandbox record; cannot delete.",{"record_id":{"type":"string"},"status":{"type":"string","enum":["active","open","in_progress","blocked","done","review","pending_review","investigating","closed"]},"note":{"type":"string"}},["record_id","status","note"]),
      "draft_message":("Save a message draft locally. This never sends a message.",{"recipient":{"type":"string"},"subject":{"type":"string"},"body":{"type":"string"}},["recipient","subject","body"])
    }
    if agent_type not in {"knowledge","workflow"}:
        raise ValueError(f"Unknown agent type: {agent_type}")
    selected = KNOWLEDGE_TOOLS if agent_type == "knowledge" else WORKFLOW_TOOLS
    return [{"type":"function","name":name,"description":definitions[name][0],
             "parameters":{"type":"object","properties":definitions[name][1],"required":definitions[name][2],"additionalProperties":False},"strict":True}
            for name in sorted(selected)]
