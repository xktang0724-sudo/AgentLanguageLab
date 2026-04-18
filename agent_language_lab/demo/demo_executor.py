from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from agent_language_lab.agent.action_executor import ToolDefinition, ToolRegistry
from agent_language_lab.agent.types import ExecutionContext
from agent_language_lab.demo.tool_catalog import ORDER_STATUS_VALUES

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
        value = as_record(input_value)
        return LookupOrderInput(order_id=read_required_string(value, "orderId"))

    async def execute(
        self,
        input_value: LookupOrderInput,
        context: ExecutionContext,
    ) -> LookupOrderOutput:
        if "orders:read" not in context.permissions:
            raise ValueError("Missing permission: orders:read")

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
        return DraftReplyOutput(draft=create_draft_reply(input_value))


class DemoExecutor(ToolRegistry):
    def __init__(self) -> None:
        super().__init__(
            {
                LookupOrderTool.name: LookupOrderTool(),
                DraftReplyTool.name: DraftReplyTool(),
            }
        )


def create_draft_reply(input_value: DraftReplyInput) -> str:
    if input_value.status == "not_found":
        return (
            f"I couldn't find order {input_value.order_id}. "
            "Please confirm the order number so I can check again."
        )

    if input_value.status == "processing":
        return (
            f"Your order {input_value.order_id} is still processing. "
            f"The current estimated delivery date is {input_value.estimated_delivery}."
        )

    if input_value.status == "shipped":
        return (
            f"Your order {input_value.order_id} has shipped and is expected to arrive "
            f"by {input_value.estimated_delivery}."
        )

    return (
        f"Your order {input_value.order_id} is delayed. "
        f"The latest estimated delivery date is {input_value.estimated_delivery}."
    )


def as_record(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("Tool input must be an object")
    return value


def read_required_string(value: dict[str, Any], key: str) -> str:
    field = value.get(key)
    if not isinstance(field, str) or not field:
        raise ValueError(f"{key} must be a non-empty string")
    return field
