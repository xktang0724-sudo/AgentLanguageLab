from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping, TypeAlias


AgentSessionStatus: TypeAlias = Literal[
    "running",
    "completed",
    "needs_user_input",
    "handoff_requested",
    "failed",
    "max_steps_exceeded",
]

AgentRunStatus: TypeAlias = Literal[
    "completed",
    "needs_user_input",
    "handoff_requested",
    "max_steps_exceeded",
]


@dataclass(frozen=True, slots=True)
class FinalAnswerAction:
    answer: str
    type: Literal["final_answer"] = field(default="final_answer", init=False)


@dataclass(frozen=True, slots=True)
class AskUserAction:
    question: str
    type: Literal["ask_user"] = field(default="ask_user", init=False)


@dataclass(frozen=True, slots=True)
class HandoffToHumanAction:
    reason: str
    type: Literal["handoff_to_human"] = field(default="handoff_to_human", init=False)


@dataclass(frozen=True, slots=True)
class ToolCallAction:
    call_id: str
    tool_name: str
    input: Any
    type: Literal["tool_call"] = field(default="tool_call", init=False)


AgentAction: TypeAlias = (
    FinalAnswerAction | AskUserAction | HandoffToHumanAction | ToolCallAction
)


@dataclass(frozen=True, slots=True)
class ExecutionContext:
    session_id: str
    current_step: int
    trace_id: str
    user_id: str | None
    permissions: tuple[str, ...]
    metadata: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class ToolObservation:
    call_id: str
    tool_name: str
    ok: bool
    output: Any = None
    error: str | None = None
    kind: Literal["tool_result"] = field(default="tool_result", init=False)


@dataclass(frozen=True, slots=True)
class Message:
    role: Literal["user", "assistant", "tool"]
    content: Any


@dataclass(frozen=True, slots=True)
class ModelDecisionTraceItem:
    action: AgentAction
    kind: Literal["model_decision"] = field(default="model_decision", init=False)


@dataclass(frozen=True, slots=True)
class ToolObservationTraceItem:
    action: ToolCallAction
    observation: ToolObservation
    kind: Literal["tool_observation"] = field(default="tool_observation", init=False)


AgentTraceItem: TypeAlias = ModelDecisionTraceItem | ToolObservationTraceItem


@dataclass(frozen=True, slots=True)
class ModelContextView:
    session_id: str
    user_input: str
    current_step: int
    model_call_count: int
    tool_call_count: int
    recent_events: tuple[AgentTraceItem, ...]
    messages: tuple[Message, ...]
    permissions: tuple[str, ...]
    metadata: Mapping[str, Any] | None = None


@dataclass(slots=True)
class AgentSessionState:
    session_id: str
    trace_id: str
    user_id: str | None
    user_input: str
    current_step: int
    model_call_count: int
    tool_call_count: int
    status: AgentSessionStatus
    permissions: list[str]
    messages: list[Message]
    trace: list[AgentTraceItem]
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class AgentRunResult:
    status: AgentRunStatus
    answer: str | None
    question: str | None
    handoff_reason: str | None
    steps: int
    model_call_count: int
    tool_call_count: int
    trace: tuple[AgentTraceItem, ...]
