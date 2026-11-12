"""Native local Ollama adapter with bounded, non-thinking Qwen tool calls."""
from __future__ import annotations

import json
import os
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

from .agents import AGENT_INSTRUCTIONS, BASE_INSTRUCTIONS, VERIFIED_ADDENDUM
from .models import AgentRun, TraceEvent
from .tools import Sandbox, tool_schemas


def _native_api_root(client: Any) -> str:
    """Resolve the native Ollama host from the configured OpenAI-style base URL."""
    configured = getattr(client, "base_url", None)
    raw = str(configured or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1/"))
    parsed = urlsplit(raw)
    path = parsed.path.rstrip("/")
    for suffix in ("/v1/chat/completions", "/v1"):
        if path.endswith(suffix):
            path = path[: -len(suffix)]
            break
    return urlunsplit((parsed.scheme, parsed.netloc, path, "", "")).rstrip("/")


def _chat_tools(agent_type: str) -> list[dict[str, Any]]:
    """Convert the shared Responses-style schemas to Ollama's native tool format."""
    return [
        {
            "type": "function",
            "function": {
                "name": schema["name"],
                "description": schema["description"],
                "parameters": schema["parameters"],
            },
        }
        for schema in tool_schemas(agent_type)
    ]


def _has_full_document_retrieval(trace: list[TraceEvent]) -> bool:
    """Return true only when get_document produced non-empty full source content."""
    return any(
        event.event_type == "tool_result"
        and event.tool_name == "get_document"
        and isinstance(event.result, dict)
        and str(event.result.get("id", "")).startswith("DOC-")
        and isinstance(event.result.get("content"), str)
        and bool(event.result["content"].strip())
        for event in trace
    )


def _retrieved_document_ids(trace: list[TraceEvent]) -> list[str]:
    """Return IDs for full documents successfully retrieved in this run."""
    return list(dict.fromkeys(
        str(event.result["id"])
        for event in trace
        if event.event_type == "tool_result"
        and event.tool_name == "get_document"
        and isinstance(event.result, dict)
        and str(event.result.get("id", "")).startswith("DOC-")
        and isinstance(event.result.get("content"), str)
        and event.result["content"].strip()
    ))


def _num_predict() -> int:
    raw = os.getenv("OLLAMA_NUM_PREDICT", "2048")
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError("OLLAMA_NUM_PREDICT must be an integer.") from exc
    if not 256 <= value <= 8192:
        raise ValueError("OLLAMA_NUM_PREDICT must be between 256 and 8192.")
    return value


def _post_chat(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=300) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")[:1000]
        raise RuntimeError(f"Ollama HTTP {exc.code}: {details or exc.reason}") from exc
    except URLError as exc:
        raise RuntimeError(
            f"Could not reach the local Ollama server at {url}: {exc.reason}"
        ) from exc
    if not isinstance(data, dict):
        raise RuntimeError("Ollama returned a malformed chat response.")
    return data


def run_ollama_agent(
    case: dict[str, Any],
    sandbox: Sandbox,
    client: Any,
    model: str,
    strategy: str = "baseline",
    allow_writes: bool = False,
    max_tool_calls: int = 8,
) -> AgentRun:
    """Run one case against Ollama's native /api/chat endpoint.

    Qwen3 thinking is explicitly disabled for this tool-use benchmark. This keeps
    reasoning tokens from consuming the response budget before a function call or
    final answer is returned. All tool execution still passes through Sandbox.call.
    """
    started = time.perf_counter()
    trace: list[TraceEvent] = []
    input_tokens = 0
    output_tokens = 0
    calls_used = 0
    retrieval_reminders = 0
    citation_reminders = 0
    agent_type = case.get("agent_type", "")
    case_id = str(case.get("id", "unknown"))
    endpoint = f"{_native_api_root(client)}/api/chat"

    try:
        if agent_type not in AGENT_INSTRUCTIONS:
            raise ValueError(f"Unknown agent type: {agent_type}")
        if strategy not in {"baseline", "verified"}:
            raise ValueError(f"Unknown strategy: {strategy}")
        if max_tool_calls < 1:
            raise ValueError("max_tool_calls must be at least 1")

        instructions = BASE_INSTRUCTIONS + AGENT_INSTRUCTIONS[agent_type]
        if strategy == "verified":
            instructions += VERIFIED_ADDENDUM
        if agent_type == "knowledge":
            instructions += (
                "\nMandatory retrieval gate: do not answer from search snippets. "
                "After search_documents returns relevant document IDs, copy the exact "
                "source ID and call get_document with exactly {document_id: \"DOC-001\"}. "
                "Never pass query or limit to get_document; those arguments belong only "
                "to search_documents. Read the full returned content. If you have not "
                "successfully called get_document, you must call it before producing any "
                "final answer. Do not include analysis or planning."
            )

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": instructions},
            {"role": "user", "content": case["task"]},
        ]
        tools = _chat_tools(agent_type)
        num_predict = _num_predict()

        while True:
            response = _post_chat(
                endpoint,
                {
                    "model": model,
                    "messages": messages,
                    "tools": tools,
                    "stream": False,
                    "think": False,
                    "options": {"num_predict": num_predict},
                },
            )
            input_tokens += int(response.get("prompt_eval_count") or 0)
            output_tokens += int(response.get("eval_count") or 0)

            if response.get("done_reason") == "length":
                raise RuntimeError(
                    f"Ollama response reached the {num_predict}-token output limit. "
                    "Increase OLLAMA_NUM_PREDICT or inspect the model trace."
                )

            message = response.get("message")
            if not isinstance(message, dict):
                raise RuntimeError("Ollama returned no assistant message.")
            function_calls = message.get("tool_calls") or []
            assistant_message = {
                "role": "assistant",
                "content": str(message.get("content") or ""),
            }
            if function_calls:
                assistant_message["tool_calls"] = function_calls
            messages.append(assistant_message)

            if not function_calls:
                final_output = assistant_message["content"].strip()
                if agent_type == "knowledge" and not _has_full_document_retrieval(trace):
                    if retrieval_reminders >= 2:
                        raise RuntimeError(
                            "Knowledge Agent returned a final answer without retrieving "
                            "a full source document with get_document. The answer was not accepted."
                        )
                    retrieval_reminders += 1
                    trace.append(TraceEvent(
                        index=len(trace) + 1,
                        event_type="retrieval_gate",
                        message=(
                            "Final answer paused: no full source document was retrieved. "
                            "The model was asked to call get_document before answering."
                        ),
                    ))
                    messages.append({
                        "role": "user",
                        "content": (
                            "Your final answer is not accepted yet. You used only search "
                            "results, which are snippets. Call get_document with the ID of "
                            "the relevant search result, read its full content, and then "
                            "give a concise answer with the source citation. Do not describe "
                            "your analysis."
                        ),
                    })
                    continue

                if agent_type == "knowledge":
                    required_ids = [
                        str(doc_id)
                        for doc_id in case.get("expected", {}).get("required_doc_ids", [])
                    ] or _retrieved_document_ids(trace)
                    missing_citations = [
                        doc_id for doc_id in required_ids
                        if f"[{doc_id}]".casefold() not in final_output.casefold()
                    ]
                    if missing_citations:
                        if citation_reminders >= 1:
                            raise RuntimeError(
                                "Knowledge Agent returned an answer without the required "
                                f"source citation(s): {', '.join(missing_citations)}."
                            )
                        citation_reminders += 1
                        trace.append(TraceEvent(
                            index=len(trace) + 1,
                            event_type="citation_gate",
                            message=(
                                "Final answer paused: required source citation(s) are missing: "
                                + ", ".join(missing_citations)
                            ),
                        ))
                        source_content = [
                            event.result.get("content", "")
                            for event in trace
                            if event.event_type == "tool_result"
                            and event.tool_name == "get_document"
                            and isinstance(event.result, dict)
                            and event.result.get("id") in missing_citations
                        ]
                        messages.append({
                            "role": "user",
                            "content": (
                                "Your answer is incomplete because it omitted the required "
                                "source citation(s): "
                                + ", ".join(f"[{doc_id}]" for doc_id in missing_citations)
                                + ". Re-read the full source content already retrieved and "
                                "return a concise corrected answer with those exact citation "
                                "markers. Preserve the source's meaning precisely: keep the "
                                "same actor, action, object, and timing; do not change what "
                                "a deadline applies to. Do not include analysis or planning.\n"
                                + "\n".join(source_content)
                            ),
                        })
                        continue

                # Qwen3 may include a visible closing think marker in content on some
                # Ollama/model versions. Keep only the answer after that marker.
                if "</think>" in final_output:
                    final_output = final_output.rsplit("</think>", 1)[-1].strip()
                trace.append(TraceEvent(
                    index=len(trace) + 1,
                    event_type="final",
                    message="Ollama returned its final response.",
                    result=final_output,
                ))
                run = AgentRun(
                    case_id=case_id,
                    agent_type=agent_type,
                    strategy=strategy,
                    status="completed" if final_output else "empty_output",
                    final_output=final_output,
                    trace=trace,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )
                break

            for call in function_calls:
                calls_used += 1
                if calls_used > max_tool_calls:
                    raise RuntimeError(f"Tool-call limit ({max_tool_calls}) reached.")

                function = call.get("function") if isinstance(call, dict) else None
                if not isinstance(function, dict):
                    raise ValueError("Ollama returned a malformed function call.")
                name = str(function.get("name") or "")
                arguments = function.get("arguments")
                if not isinstance(arguments, dict):
                    raise ValueError(f"Tool '{name}' arguments must be a JSON object.")

                call_started = time.perf_counter()
                result, event_type = sandbox.call(
                    name, arguments, agent_type, allow_writes=allow_writes
                )
                duration_ms = (time.perf_counter() - call_started) * 1000
                trace.append(TraceEvent(
                    index=len(trace) + 1,
                    event_type="tool_call",
                    message=f"Model requested {name}.",
                    tool_name=name,
                    arguments=arguments,
                ))
                trace.append(TraceEvent(
                    index=len(trace) + 1,
                    event_type=event_type,
                    message=f"{name} returned {event_type.replace('_', ' ')}.",
                    tool_name=name,
                    result=result,
                    duration_ms=round(duration_ms, 3),
                ))
                messages.append({
                    "role": "tool",
                    "tool_name": name,
                    "content": json.dumps(result, ensure_ascii=False),
                })

        run.latency_ms = (time.perf_counter() - started) * 1000
        return run

    except Exception as exc:
        latency_ms = (time.perf_counter() - started) * 1000
        trace.append(TraceEvent(
            index=len(trace) + 1,
            event_type="run_error",
            message=f"Model run stopped: {type(exc).__name__}: {exc}",
        ))
        return AgentRun(
            case_id=case_id,
            agent_type=agent_type,
            strategy=strategy,
            status="error",
            trace=trace,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            error=f"{type(exc).__name__}: {exc}",
        )
