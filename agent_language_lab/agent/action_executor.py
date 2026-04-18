from __future__ import annotations

import inspect
from typing import Any, Awaitable, Mapping, Protocol, TypeVar

from agent_language_lab.agent.types import ExecutionContext, ToolCallAction, ToolObservation

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


class ToolDefinition(Protocol[InputT, OutputT]):
    name: str
    description: str

    def validate(self, input_value: Any) -> InputT:
        """Parse and validate incoming tool input."""

    def execute(
        self,
        input_value: InputT,
        context: ExecutionContext,
    ) -> OutputT | Awaitable[OutputT]:
        """Execute the tool."""


class ActionExecutor(Protocol):
    async def execute_tool_call(
        self,
        action: ToolCallAction,
        context: ExecutionContext,
    ) -> ToolObservation:
        """Execute a tool call action."""


class ToolRegistry(ActionExecutor):
    def __init__(self, tools: Mapping[str, ToolDefinition[Any, Any]]) -> None:
        self._tools = dict(tools)

    async def execute_tool_call(
        self,
        action: ToolCallAction,
        context: ExecutionContext,
    ) -> ToolObservation:
        tool = self._tools.get(action.tool_name)
        if tool is None:
            return ToolObservation(
                call_id=action.call_id,
                tool_name=action.tool_name,
                ok=False,
                error=f"Unknown tool: {action.tool_name}",
            )

        try:
            parsed_input = tool.validate(action.input)
            output = tool.execute(parsed_input, context)
            if inspect.isawaitable(output):
                output = await output

            return ToolObservation(
                call_id=action.call_id,
                tool_name=action.tool_name,
                ok=True,
                output=output,
            )
        except Exception as error:  # noqa: BLE001 - phase 1 keeps tool failures simple
            return ToolObservation(
                call_id=action.call_id,
                tool_name=action.tool_name,
                ok=False,
                error=str(error) or "Unknown tool error",
            )
