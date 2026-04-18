from __future__ import annotations

import re

from agent_language_lab.agent.model_client import ModelClient
from agent_language_lab.agent.types import (
    AgentAction,
    FinalAnswerAction,
    HandoffToHumanAction,
    ModelContextView,
    ToolObservation,
    ToolObservationTraceItem,
    ToolCallAction,
    AskUserAction,
)
from agent_language_lab.demo.demo_executor import DraftReplyOutput, LookupOrderOutput


class DemoModel(ModelClient):
    async def decide_next_action(self, context: ModelContextView) -> AgentAction:
        if contains_escalation_signal(context.user_input):
            return HandoffToHumanAction(
                reason=(
                    "This request has fraud or legal risk and should be reviewed "
                    "by a human agent."
                )
            )

        order_id = extract_order_id(context.user_input)
        if order_id is None:
            return AskUserAction(
                question=(
                    "Please share your order number in the format ORD-1234 "
                    "so I can check the status."
                )
            )

        lookup_observation = find_tool_observation(context, "lookupOrder")
        if lookup_observation is None:
            return ToolCallAction(
                call_id=f"call-{context.current_step + 1}-lookup-order",
                tool_name="lookupOrder",
                input={
                    "orderId": order_id,
                },
            )

        if not lookup_observation.ok or lookup_observation.output is None:
            return HandoffToHumanAction(
                reason="Order lookup failed and needs human review."
            )

        draft_observation = find_tool_observation(context, "draftReply")
        if draft_observation is None:
            lookup_output = lookup_observation.output
            if not isinstance(lookup_output, LookupOrderOutput):
                raise ValueError("lookupOrder returned an unexpected output shape")

            return ToolCallAction(
                call_id=f"call-{context.current_step + 1}-draft-reply",
                tool_name="draftReply",
                input={
                    "orderId": lookup_output.order_id,
                    "status": lookup_output.status,
                    "estimatedDelivery": lookup_output.estimated_delivery,
                },
            )

        if not draft_observation.ok or draft_observation.output is None:
            return HandoffToHumanAction(
                reason="Reply drafting failed and needs human review."
            )

        draft_output = draft_observation.output
        if not isinstance(draft_output, DraftReplyOutput):
            raise ValueError("draftReply returned an unexpected output shape")

        return FinalAnswerAction(answer=draft_output.draft)


def contains_escalation_signal(user_input: str) -> bool:
    return re.search(r"\b(chargeback|fraud|lawyer|legal)\b", user_input, re.IGNORECASE) is not None


def extract_order_id(user_input: str) -> str | None:
    match = re.search(r"\bORD-\d+\b", user_input, re.IGNORECASE)
    if match is None:
        return None
    return match.group(0).upper()


def find_tool_observation(
    context: ModelContextView,
    tool_name: str,
) -> ToolObservation | None:
    for event in reversed(context.recent_events):
        if (
            isinstance(event, ToolObservationTraceItem)
            and event.observation.tool_name == tool_name
        ):
            return event.observation

    return None
