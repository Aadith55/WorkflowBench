"""Small data models shared by the runner, tools and evaluator."""
from dataclasses import asdict, dataclass, field
from typing import Any

@dataclass
class TraceEvent:
    index: int
    event_type: str
    message: str
    tool_name: str | None = None
    arguments: dict[str, Any] = field(default_factory=dict)
    result: Any = None
    duration_ms: float | None = None
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass
class AgentRun:
    case_id: str
    agent_type: str
    strategy: str
    status: str
    final_output: str = ""
    trace: list[TraceEvent] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    estimated_cost_usd: float | None = None
    error: str | None = None
    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id, "agent_type": self.agent_type, "strategy": self.strategy,
            "status": self.status, "final_output": self.final_output,
            "trace": [event.to_dict() for event in self.trace],
            "input_tokens": self.input_tokens, "output_tokens": self.output_tokens,
            "latency_ms": self.latency_ms, "estimated_cost_usd": self.estimated_cost_usd,
            "error": self.error,
        }
