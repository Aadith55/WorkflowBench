"""Gemini adapter using its OpenAI-compatible Chat Completions endpoint."""
from __future__ import annotations

import json
import time
from typing import Any

from .agents import AGENT_INSTRUCTIONS, BASE_INSTRUCTIONS, VERIFIED_ADDENDUM
from .models import AgentRun, TraceEvent
from .tools import Sandbox, tool_schemas


def _usage_value(response: Any, name: str) -> int:
    usage = getattr(response, "usage", None)
    value = getattr(usage, name, 0) if usage is not None else 0
    return int(value or 0)


def _chat_tools(agent_type: str) -> list[dict[str, Any]]:
    """Convert Responses-style local schemas into Chat Completions tool schemas."""
    converted = []
    for schema in tool_schemas(agent_type):
        converted.append({
            "type": "function",
            "function": {
                "name": schema["name"],
                "description": schema["description"],
                "parameters": schema["parameters"],
            },
        })
    return converted


def run_gemini_agent(
    case: dict[str, Any],
    sandbox: Sandbox,
    client: Any,
    model: str,
    strategy: str = "baseline",
    allow_writes: bool = False,
    max_tool_calls: int = 8,
) -> AgentRun:
    """Run one case against Gemini's OpenAI-compatible Chat Completions API."""
    started = time.perf_counter()
    trace: list[TraceEvent] = []
    input_tokens = 0
    output_tokens = 0
    calls_used = 0
    agent_type = case["agent_type"]
    case_id = str(case.get("id", "unknown"))

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

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": instructions},
            {"role": "user", "content": case["task"]},
        ]
        tools = _chat_tools(agent_type)

        while True:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                max_tokens=1200,
            )
            choices = getattr(response, "choices", None) or []
            if not choices:
                raise RuntimeError("Chat Completions API returned no choices.")

            choice = choices[0]
            if getattr(choice, "finish_reason", None) == "length":
                raise RuntimeError("Chat Completions response was truncated at the token limit.")

            input_tokens += _usage_value(response, "prompt_tokens")
            output_tokens += _usage_value(response, "completion_tokens")
            message = getattr(choice, "message", None)
            if message is None:
                raise RuntimeError("Chat Completions API returned no assistant message.")

            function_calls = list(getattr(message, "tool_calls", None) or [])
            if not function_calls:
                final_output = str(getattr(message, "content", None) or "").strip()
                trace.append(TraceEvent(
                    index=len(trace) + 1,
                    event_type="final",
                    message="Gemini returned its final response.",
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

            assistant_calls = []
            for call in function_calls:
                function = getattr(call, "function", None)
                if function is None:
                    raise ValueError("Gemini returned a malformed function call.")
                assistant_calls.append({
                    "id": getattr(call, "id", None),
                    "type": "function",
                    "function": {
                        "name": getattr(function, "name", ""),
                        "arguments": getattr(function, "arguments", "{}"),
                    },
                })
            messages.append({
                "role": "assistant",
                "content": getattr(message, "content", None),
                "tool_calls": assistant_calls,
            })

            for call in function_calls:
                calls_used += 1
                if calls_used > max_tool_calls:
                    raise RuntimeError(f"Tool-call limit ({max_tool_calls}) reached.")

                function = call.function
                name = str(getattr(function, "name", ""))
                raw_arguments = getattr(function, "arguments", None)
                if isinstance(raw_arguments, str):
                    arguments = json.loads(raw_arguments)
                elif isinstance(raw_arguments, dict):
                    arguments = raw_arguments
                else:
                    raise ValueError(
                        f"Tool '{name}' did not provide a JSON object of arguments."
                    )
                if not isinstance(arguments, dict):
                    raise ValueError(f"Tool '{name}' arguments must decode to a JSON object.")
                call_id = getattr(call, "id", None)
                if not call_id:
                    raise ValueError(f"Tool '{name}' did not include a call ID.")

                call_started = time.perf_counter()
                result, event_type = sandbox.call(
                    name, arguments, agent_type, allow_writes=allow_writes
                )
                duration_ms = (time.perf_counter() - call_started) * 1000
                trace.append(TraceEvent(
                    index=len(trace) + 1,
                    event_type="tool_call",
                    message=f"Gemini requested {name}.",
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
                    "tool_call_id": call_id,
                    "content": json.dumps(result, ensure_ascii=False),
                })

        run.latency_ms = (time.perf_counter() - started) * 1000
        return run

    except Exception as exc:
        latency_ms = (time.perf_counter() - started) * 1000
        trace.append(TraceEvent(
            index=len(trace) + 1,
            event_type="run_error",
            message=f"Gemini run stopped: {type(exc).__name__}: {exc}",
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
