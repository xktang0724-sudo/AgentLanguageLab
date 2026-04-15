import type {
  ExecutionContext,
  ToolCallAction,
  ToolDefinition,
  ToolObservation,
} from "./types.js";

export interface ActionExecutor {
  executeToolCall(action: ToolCallAction, context: ExecutionContext): Promise<ToolObservation>;
}

export class ToolRegistry implements ActionExecutor {
  constructor(
    private readonly tools: ReadonlyMap<string, ToolDefinition<unknown, unknown>>,
  ) {}

  async executeToolCall(action: ToolCallAction, context: ExecutionContext): Promise<ToolObservation> {
    const tool = this.tools.get(action.toolName);

    if (!tool) {
      return {
        kind: "tool_result",
        callId: action.callId,
        toolName: action.toolName,
        ok: false,
        error: `Unknown tool: ${action.toolName}`,
      };
    }

    try {
      const parsedInput = tool.validate(action.input);
      const output = await tool.execute(parsedInput, context);

      return {
        kind: "tool_result",
        callId: action.callId,
        toolName: action.toolName,
        ok: true,
        output,
      };
    } catch (error) {
      return {
        kind: "tool_result",
        callId: action.callId,
        toolName: action.toolName,
        ok: false,
        error: error instanceof Error ? error.message : "Unknown tool error",
      };
    }
  }
}
