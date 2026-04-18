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


async def run_agent_loop(input_value: RunAgentLoopInput) -> AgentRunResult:
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
            context = create_model_context_view(state)
            action = await input_value.model.decide_next_action(context)
            state.model_call_count += 1
            state.trace.append(ModelDecisionTraceItem(action=action))

            terminal_result = handle_terminal_action(state, action)
            if terminal_result is not None:
                return terminal_result

            if not isinstance(action, ToolCallAction):
                raise ValueError(f"Unsupported action type: {action.type}")

            observation = await input_value.executor.execute_tool_call(
                action,
                create_execution_context(state),
            )
            state.tool_call_count += 1
            state.trace.append(ToolObservationTraceItem(action=action, observation=observation))
            state.messages.append(create_tool_message(action, observation))
            state.current_step += 1
    except Exception:
        state.status = "failed"
        raise

    state.status = "max_steps_exceeded"
    return create_run_result(state, answer=None)


def create_run_result(state: AgentSessionState, answer: str | None) -> AgentRunResult:
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


def create_execution_context(state: AgentSessionState) -> ExecutionContext:
    return ExecutionContext(
        session_id=state.session_id,
        current_step=state.current_step,
        trace_id=state.trace_id,
        user_id=state.user_id,
        permissions=tuple(state.permissions),
        metadata=snapshot_metadata(state.metadata),
    )


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
    if status in {"completed", "needs_user_input", "handoff_requested"}:
        return status
    return "max_steps_exceeded"


def snapshot_trace(trace: list[Any]) -> tuple[Any, ...]:
    return tuple(copy.deepcopy(trace))


def snapshot_messages(messages: list[Message]) -> tuple[Message, ...]:
    return tuple(copy.deepcopy(messages))


def snapshot_metadata(metadata: dict[str, Any] | None) -> Mapping[str, Any] | None:
    if metadata is None:
        return None
    return MappingProxyType(copy.deepcopy(metadata))


def create_session_id() -> str:
    return f"session-{uuid.uuid4().hex}"


def create_trace_id() -> str:
    return f"trace-{uuid.uuid4().hex}"
