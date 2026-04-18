from __future__ import annotations

import inspect
from typing import Any, Awaitable, Mapping, Protocol, TypeVar

from agent_language_lab.agent.types import ExecutionContext, ToolCallAction, ToolObservation

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


# 工具定义协议：每个工具负责参数校验与执行，统一输出任意类型
class ToolDefinition(Protocol[InputT, OutputT]):
    name: str
    description: str

    def validate(self, input_value: Any) -> InputT:
        """校验/转换工具输入，返回工具内部期望的结构。"""

    def execute(
        self,
        input_value: InputT,
        context: ExecutionContext,
    ) -> OutputT | Awaitable[OutputT]:
        """执行工具，可支持同步或异步实现。"""


# 执行器协议：agent_loop 只依赖 execute_tool_call 这一入口
class ActionExecutor(Protocol):
    async def execute_tool_call(
        self,
        action: ToolCallAction,
        context: ExecutionContext,
    ) -> ToolObservation:
        """执行一次工具调用，并返回可序列化的观察结果。"""


# 一个轻量注册表实现：按工具名路由到具体 ToolDefinition
class ToolRegistry(ActionExecutor):
    def __init__(self, tools: Mapping[str, ToolDefinition[Any, Any]]) -> None:
        self._tools = dict(tools)

    async def execute_tool_call(
        self,
        action: ToolCallAction,
        context: ExecutionContext,
    ) -> ToolObservation:
        # 1) 不存在的工具直接返回失败观察，不抛异常，保持 loop 流程可继续
        tool = self._tools.get(action.tool_name)
        if tool is None:
            return ToolObservation(
                call_id=action.call_id,
                tool_name=action.tool_name,
                ok=False,
                error=f"Unknown tool: {action.tool_name}",
            )

        try:
            # 2) 先校验输入，再执行（支持 sync/async）后统一封装成功结果
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
            # 3) 工具内部任意异常都转成失败 observation，避免单次工具报错穿透到 loop
            return ToolObservation(
                call_id=action.call_id,
                tool_name=action.tool_name,
                ok=False,
                error=str(error) or "Unknown tool error",
            )
