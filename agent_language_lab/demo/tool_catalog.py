from __future__ import annotations

from dataclasses import dataclass

# Demo 场景暴露给模型/文档的工具清单
ORDER_STATUS_VALUES = ("processing", "shipped", "delayed", "not_found")


@dataclass(frozen=True, slots=True)
class DemoToolCatalogItem:
    name: str
    description: str
    when_to_use: str
    input_shape: dict[str, str]
    output_shape: dict[str, str]


# 一份结构化工具说明，可用于打印给模型或文档展示
DEMO_TOOL_CATALOG: tuple[DemoToolCatalogItem, ...] = (
    DemoToolCatalogItem(
        name="lookupOrder",
        description="Look up the latest order fulfillment status.",
        when_to_use="Use when the user has provided an order number and no order lookup result exists yet.",
        input_shape={
            "orderId": "A non-empty string like ORD-1001.",
        },
        output_shape={
            "orderId": "The normalized order number.",
            "status": f"One of: {', '.join(ORDER_STATUS_VALUES)}.",
            "estimatedDelivery": "A date string like 2026-04-18 or null when unavailable.",
        },
    ),
    DemoToolCatalogItem(
        name="draftReply",
        description="Draft a customer support reply based on the order status.",
        when_to_use="Use only after a successful lookupOrder result exists and before returning final_answer.",
        input_shape={
            "orderId": "The order number that was looked up.",
            "status": f"One of: {', '.join(ORDER_STATUS_VALUES)}.",
            "estimatedDelivery": "A date string or null.",
        },
        output_shape={
            "draft": "A natural-language reply for the customer.",
        },
    ),
)


def format_demo_tool_catalog() -> str:
    # 把结构化目录展开为可读文案，方便提示词拼接时直接嵌入
    items: list[str] = []
    for tool in DEMO_TOOL_CATALOG:
        input_lines = "\n".join(
            f"    - {key}: {value}" for key, value in tool.input_shape.items()
        )
        output_lines = "\n".join(
            f"    - {key}: {value}" for key, value in tool.output_shape.items()
        )
        items.append(
            "\n".join(
                [
                    f"- {tool.name}: {tool.description}",
                    f"  When to use: {tool.when_to_use}",
                    "  Input:",
                    input_lines,
                    "  Output:",
                    output_lines,
                ]
            )
        )

    return "\n".join(items)
