import type { ModelClient } from "../agent/model-client.js";
import type { AgentAction, ModelContextView, ToolObservation } from "../agent/types.js";

export class DemoModel implements ModelClient {
  async decideNextAction(context: ModelContextView): Promise<AgentAction> {
    if (containsEscalationSignal(context.userInput)) {
      return {
        type: "handoff_to_human",
        reason: "This request has fraud or legal risk and should be reviewed by a human agent.",
      };
    }

    const orderId = extractOrderId(context.userInput);
    if (!orderId) {
      return {
        type: "ask_user",
        question: "Please share your order number in the format ORD-1234 so I can check the status.",
      };
    }

    const lookupObservation = findToolObservation(context, "lookupOrder");
    if (!lookupObservation) {
      return {
        type: "tool_call",
        callId: `call-${context.currentStep + 1}-lookup-order`,
        toolName: "lookupOrder",
        input: {
          orderId,
        },
      };
    }
    if (!lookupObservation.ok || !lookupObservation.output) {
      return {
        type: "handoff_to_human",
        reason: "Order lookup failed and needs human review.",
      };
    }

    const draftObservation = findToolObservation(context, "draftReply");
    if (!draftObservation) {
      const lookupOutput = lookupObservation.output as {
        orderId: string;
        status: "processing" | "shipped" | "delayed" | "not_found";
        estimatedDelivery: string | null;
      };

      return {
        type: "tool_call",
        callId: `call-${context.currentStep + 1}-draft-reply`,
        toolName: "draftReply",
        input: lookupOutput,
      };
    }
    if (!draftObservation.ok || !draftObservation.output) {
      return {
        type: "handoff_to_human",
        reason: "Reply drafting failed and needs human review.",
      };
    }

    const draftOutput = draftObservation.output as { draft: string };
    return {
      type: "final_answer",
      answer: draftOutput.draft,
    };
  }
}

function containsEscalationSignal(userInput: string): boolean {
  return /\b(chargeback|fraud|lawyer|legal)\b/i.test(userInput);
}

function extractOrderId(userInput: string): string | null {
  const match = userInput.match(/\bORD-\d+\b/i);
  return match ? match[0].toUpperCase() : null;
}

function findToolObservation(
  context: ModelContextView,
  toolName: string,
): ToolObservation | null {
  for (let index = context.recentEvents.length - 1; index >= 0; index -= 1) {
    const event = context.recentEvents[index];
    if (event?.kind === "tool_observation" && event.observation.toolName === toolName) {
      return event.observation;
    }
  }

  return null;
}
