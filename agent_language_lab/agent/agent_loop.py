from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Any, Mapping

from agent_language_lab.agent.action_executor import ActionExecutor
from agent_language_lab.agent.model_client import ModelClient
from agent_language_lab.agent.types import (
    AgentAction,
    AgentRunResult,
    AgentRunStatus,
    AgentSessionState,
    AgentSessionStatus,
    AskUserAction,
    ExecutionContext,
    FinalAnswerAction,
    HandoffToHumanAction,
    Message,
    ModelContextView,
    ModelDecisionTraceItem,
    ToolCallAction,
    ToolObservation,
    ToolObservationTraceItem,
)


# run_agent_loop 的入参：封装模型、执行器和单次会话约束
@dataclass(slots=True)
class RunAgentLoopInput:
    model: ModelClient
    executor: ActionExecutor
    user_input: str
    max_steps: int
    session_id: str | None = None
    trace_id: str | None = None
    user_id: str | None = None
    permissions: tuple[str, ...] = ()
    metadata: Mapping[str, Any] | None = None


# 主循环：模型决策 -> 处理终止动作 -> 走工具 -> 写 trace -> 更新 step
async def run_agent_loop(input_value: RunAgentLoopInput) -> AgentRunResult:
    # 用显式 session/trace id 初始化会话状态，便于多会话追踪
    state = AgentSessionState(
        session_id=input_value.session_id or create_session_id(),
        trace_id=input_value.trace_id or create_trace_id(),
        user_id=input_value.user_id,
        user_input=input_value.user_input,
        current_step=0,
        model_call_count=0,
        tool_call_count=0,
        status="running",
        permissions=list(input_value.permissions),
        messages=[Message(role="user", content=input_value.user_input)],
        trace=[],
        metadata=dict(input_value.metadata) if input_value.metadata is not None else None,
    )

    try:
        while state.current_step < input_value.max_steps:
            # 每一轮先给模型一个只读快照，避免模型改写本轮内部可变列表
            context = create_model_context_view(state)
            action = await input_value.model.decide_next_action(context)
            state.model_call_count += 1
            state.trace.append(ModelDecisionTraceItem(action=action))

            terminal_result = handle_terminal_action(state, action)
            if terminal_result is not None:
                return terminal_result

            # loop 只允许 tool_call 继续推进；其余未知动作视为协议错误
            if not isinstance(action, ToolCallAction):
                raise ValueError(f"Unsupported action type: {action.type}")

            # 执行工具后把结果追加到 messages/trace，并前进一个 tool step
            observation = await input_value.executor.execute_tool_call(
                action,
                create_execution_context(state),
            )
            state.tool_call_count += 1
            state.trace.append(ToolObservationTraceItem(action=action, observation=observation))
            state.messages.append(create_tool_message(action, observation))
            state.current_step += 1
    except Exception:
        # 兜底错误仅标记失败状态并向上抛，便于调试日志与调用方捕获
        state.status = "failed"
        raise

    # 循环结束仍未命中终止动作，则视为 max_steps_exceeded
    state.status = "max_steps_exceeded"
    return create_run_result(state, answer=None)


def create_run_result(state: AgentSessionState, answer: str | None) -> AgentRunResult:
    # 将内部状态映射为对外统一返回，统一掉 failed，按协议输出上限超时状态
    return AgentRunResult(
        status=normalize_run_status(state.status),
        answer=answer,
        question=None,
        handoff_reason=None,
        steps=state.model_call_count,
        model_call_count=state.model_call_count,
        tool_call_count=state.tool_call_count,
        trace=snapshot_trace(state.trace),
    )


# 模型可见上下文：快照化事件和消息，保证可回放且防止内存别名污染
def create_model_context_view(state: AgentSessionState) -> ModelContextView:
    return ModelContextView(
        session_id=state.session_id,
        user_input=state.user_input,
        current_step=state.current_step,
        model_call_count=state.model_call_count,
        tool_call_count=state.tool_call_count,
        recent_events=snapshot_trace(state.trace),
        messages=snapshot_messages(state.messages),
        permissions=tuple(state.permissions),
        metadata=snapshot_metadata(state.metadata),
    )


# 工具执行上下文：用于授权和调用元数据校验，避免模型内部直接读写会话状态
def create_execution_context(state: AgentSessionState) -> ExecutionContext:
    return ExecutionContext(
        session_id=state.session_id,
        current_step=state.current_step,
        trace_id=state.trace_id,
        user_id=state.user_id,
        permissions=tuple(state.permissions),
        metadata=snapshot_metadata(state.metadata),
    )


# tool 消息保留标准结构，output 做 deep copy 避免后续状态污染
def create_tool_message(action: ToolCallAction, observation: ToolObservation) -> Message:
    return Message(
        role="tool",
        content={
            "call_id": action.call_id,
            "tool_name": action.tool_name,
            "ok": observation.ok,
            "output": copy.deepcopy(observation.output),
            "error": observation.error,
        },
    )


# 处理 3 类“可直接终止”动作：final/ask/handoff
def handle_terminal_action(
    state: AgentSessionState,
    action: AgentAction,
) -> AgentRunResult | None:
    if isinstance(action, FinalAnswerAction):
        state.status = "completed"
        state.messages.append(Message(role="assistant", content=action.answer))
        return create_run_result(state, answer=action.answer)

    if isinstance(action, AskUserAction):
        state.status = "needs_user_input"
        state.messages.append(Message(role="assistant", content=action.question))
        return replace(
            create_run_result(state, answer=None),
            status="needs_user_input",
            question=action.question,
        )

    if isinstance(action, HandoffToHumanAction):
        state.status = "handoff_requested"
        state.messages.append(Message(role="assistant", content=action.reason))
        return replace(
            create_run_result(state, answer=None),
            status="handoff_requested",
            handoff_reason=action.reason,
        )

    return None


def normalize_run_status(status: AgentSessionStatus) -> AgentRunStatus:
    # 只暴露允许的 run-status；失败状态归一到超步结束
    if status in {"completed", "needs_user_input", "handoff_requested"}:
        return status
    return "max_steps_exceeded"


# 深拷贝 + tuple，形成不可变快照，防止下一轮修改影响模型可见历史
def snapshot_trace(trace: list[Any]) -> tuple[Any, ...]:
    return tuple(copy.deepcopy(trace))


def snapshot_messages(messages: list[Message]) -> tuple[Message, ...]:
    return tuple(copy.deepcopy(messages))


# metadata 用 MappingProxyType 做只读包装，减少执行链被意外改写风险
def snapshot_metadata(metadata: dict[str, Any] | None) -> Mapping[str, Any] | None:
    if metadata is None:
        return None
    return MappingProxyType(copy.deepcopy(metadata))


# 用于 trace/日志聚合的可读性 id（当前仅用于测试与 debug）
def create_session_id() -> str:
    return f"session-{uuid.uuid4().hex}"


def create_trace_id() -> str:
    return f"trace-{uuid.uuid4().hex}"
