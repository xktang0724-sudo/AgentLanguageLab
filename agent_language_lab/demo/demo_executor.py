from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from agent_language_lab.agent.action_executor import ToolDefinition, ToolRegistry
from agent_language_lab.agent.types import ExecutionContext
from agent_language_lab.demo.tool_catalog import ORDER_STATUS_VALUES

# Demo 工具可接受的订单状态集合
OrderStatus = Literal["processing", "shipped", "delayed", "not_found"]


@dataclass(frozen=True, slots=True)
class LookupOrderInput:
    order_id: str


@dataclass(frozen=True, slots=True)
class LookupOrderOutput:
    order_id: str
    status: OrderStatus
    estimated_delivery: str | None


@dataclass(frozen=True, slots=True)
class DraftReplyInput:
    order_id: str
    status: OrderStatus
    estimated_delivery: str | None


@dataclass(frozen=True, slots=True)
class DraftReplyOutput:
    draft: str


# 固定的 demo 订单样例：用于演示 lookupOrder 的可预测行为
ORDER_FIXTURES: dict[str, LookupOrderOutput] = {
    "ORD-1001": LookupOrderOutput(
        order_id="ORD-1001",
        status="shipped",
        estimated_delivery="2026-04-18",
    ),
    "ORD-1002": LookupOrderOutput(
        order_id="ORD-1002",
        status="processing",
        estimated_delivery="2026-04-20",
    ),
    "ORD-4040": LookupOrderOutput(
        order_id="ORD-4040",
        status="delayed",
        estimated_delivery="2026-04-22",
    ),
}


class LookupOrderTool(ToolDefinition[LookupOrderInput, LookupOrderOutput]):
    name = "lookupOrder"
    description = "Look up the latest order fulfillment status."

    def validate(self, input_value: Any) -> LookupOrderInput:
        # 形状校验：入参必须是对象，且 orderId 为非空字符串
        value = as_record(input_value)
        return LookupOrderInput(order_id=read_required_string(value, "orderId"))

    async def execute(
        self,
        input_value: LookupOrderInput,
        context: ExecutionContext,
    ) -> LookupOrderOutput:
        # 当前示例环境通过权限校验防止越权读取订单
        if "orders:read" not in context.permissions:
            raise ValueError("Missing permission: orders:read")

        # 未命中时返回 not_found，保持工具总是成功返回结构化结果
        return ORDER_FIXTURES.get(
            input_value.order_id,
            LookupOrderOutput(
                order_id=input_value.order_id,
                status="not_found",
                estimated_delivery=None,
            ),
        )


class DraftReplyTool(ToolDefinition[DraftReplyInput, DraftReplyOutput]):
    name = "draftReply"
    description = "Draft a customer support reply based on the order status."

    def validate(self, input_value: Any) -> DraftReplyInput:
        # 支持 estimatedDelivery 可空；status 必须在白名单内
        value = as_record(input_value)
        estimated_delivery = value.get("estimatedDelivery")
        if estimated_delivery is not None and not isinstance(estimated_delivery, str):
            raise ValueError("estimatedDelivery must be a string or null")

        status = read_required_string(value, "status")
        if status not in ORDER_STATUS_VALUES:
            raise ValueError(f"Unsupported order status: {status}")

        return DraftReplyInput(
            order_id=read_required_string(value, "orderId"),
            status=status,
            estimated_delivery=estimated_delivery,
        )

    async def execute(
        self,
        input_value: DraftReplyInput,
        context: ExecutionContext,
    ) -> DraftReplyOutput:
        # 直接按模板生成草稿，不访问外部服务
        return DraftReplyOutput(draft=create_draft_reply(input_value))


class DemoExecutor(ToolRegistry):
    def __init__(self) -> None:
        # 注册可用工具：lookupOrder + draftReply
        super().__init__(
            {
                LookupOrderTool.name: LookupOrderTool(),
                DraftReplyTool.name: DraftReplyTool(),
            }
        )


def create_draft_reply(input_value: DraftReplyInput) -> str:
    # 1) 订单不存在：提示复核订单号
    if input_value.status == "not_found":
        return (
            f"I couldn't find order {input_value.order_id}. "
            "Please confirm the order number so I can check again."
        )

    # 2) 处理中/已发运：给出可读文本
    if input_value.status == "processing":
        return (
            f"Your order {input_value.order_id} is still processing. "
            f"The current estimated delivery date is {input_value.estimated_delivery}."
        )

    # 3) 已发货：告知预计到达日
    if input_value.status == "shipped":
        return (
            f"Your order {input_value.order_id} has shipped and is expected to arrive "
            f"by {input_value.estimated_delivery}."
        )

    # 4) 其它状态按延迟模板兜底
    return (
        f"Your order {input_value.order_id} is delayed. "
        f"The latest estimated delivery date is {input_value.estimated_delivery}."
    )


def as_record(value: Any) -> dict[str, Any]:
    # 工具输入要求对象类型，否则直接拒绝
    if not isinstance(value, dict):
        raise ValueError("Tool input must be an object")
    return value


def read_required_string(value: dict[str, Any], key: str) -> str:
    # 读取字段并确保是非空字符串
    field = value.get(key)
    if not isinstance(field, str) or not field:
        raise ValueError(f"{key} must be a non-empty string")
    return field
def as_record(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("Tool input must be an object")
    return value


def read_required_string(value: dict[str, Any], key: str) -> str:
    field = value.get(key)
    if not isinstance(field, str) or not field:
        raise ValueError(f"{key} must be a non-empty string")
    return field
