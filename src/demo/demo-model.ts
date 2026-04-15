import type { ModelClient } from "../agent/model-client.js";
import type { AgentAction, ModelContextView } from "../agent/types.js";

export class DemoModel implements ModelClient {
  async decideNextAction(context: ModelContextView): Promise<AgentAction> {
    const hasBuiltinResult = context.recentEvents.some((item) => item.kind === "action_result");

    if (!hasBuiltinResult) {
      return {
        type: "builtin_call",
        name: "echo",
        input: {
          text: context.userInput,
        },
      };
    }

    return {
      type: "final_answer",
      answer: `Done: ${context.userInput}`,
    };
  }
}
