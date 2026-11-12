"""Local Ollama adapter for the shared OpenAI-compatible chat runner."""
from __future__ import annotations

from typing import Any

from .gemini_agent import run_gemini_agent
from .models import AgentRun
from .tools import Sandbox


def run_ollama_agent(
    case: dict[str, Any],
    sandbox: Sandbox,
    client: Any,
    model: str,
    strategy: str = "baseline",
    allow_writes: bool = False,
    max_tool_calls: int = 8,
) -> AgentRun:
    """Run a scenario against a local Ollama server without cloud API credentials.

    Ollama's local OpenAI-compatible endpoint supports tools but does not currently
    document the OpenAI tool_choice request field, so the shared runner omits it.
    """
    return run_gemini_agent(
        case=case,
        sandbox=sandbox,
        client=client,
        model=model,
        strategy=strategy,
        allow_writes=allow_writes,
        max_tool_calls=max_tool_calls,
        tool_choice=None,
    )
