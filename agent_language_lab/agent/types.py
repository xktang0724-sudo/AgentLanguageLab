from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping, TypeAlias


# 会话状态：完整过程中的内部状态与最终返回给上层的结果状态
AgentSessionStatus: TypeAlias = Literal[
    "running",
    "completed",
    "needs_user_input",
    "handoff_requested",
    "failed",
    "max_steps_exceeded",
]

# 对外输出的 run 状态（失败在外层归一化为超步上限）
AgentRunStatus: TypeAlias = Literal[
    "completed",
    "needs_user_input",
    "handoff_requested",
    "max_steps_exceeded",
]


# 四类动作：模型每次只能返回一条下一步指令
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


# Agent 每一轮决策可能返回的统一动作类型
AgentAction: TypeAlias = (
    FinalAnswerAction | AskUserAction | HandoffToHumanAction | ToolCallAction
)


# 给工具执行器提供的上下文，避免把完整状态直接暴露给工具
@dataclass(frozen=True, slots=True)
class ExecutionContext:
    session_id: str
    current_step: int
    trace_id: str
    user_id: str | None
    permissions: tuple[str, ...]
    metadata: Mapping[str, Any] | None = None


# 工具执行结果：成功/失败都要可追踪，便于 loop 和结果归因
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


# 给 trace 使用的动作记录：模型决策和工具观察两种事件
@dataclass(frozen=True, slots=True)
class ModelDecisionTraceItem:
    action: AgentAction
    kind: Literal["model_decision"] = field(default="model_decision", init=False)


@dataclass(frozen=True, slots=True)
class ToolObservationTraceItem:
    action: ToolCallAction
    observation: ToolObservation
    kind: Literal["tool_observation"] = field(default="tool_observation", init=False)


# trace 中只保存这两种事件，便于模型视图和审计重放
AgentTraceItem: TypeAlias = ModelDecisionTraceItem | ToolObservationTraceItem


# 传给模型的只读视图：包含历史 trace、消息与计数器，避免模型修改可变状态
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


# 运行时内部状态：loop 专属，持续更新
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


# 统一返回结构：前端/CLI 只看这个结果，不直接依赖内部 state
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
