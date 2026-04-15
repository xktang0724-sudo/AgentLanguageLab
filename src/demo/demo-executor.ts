import type { ActionExecutor } from "../agent/action-executor.js";
import type { BuiltinCallAction, BuiltinResult, ExecutionContext } from "../agent/types.js";

export type BuiltinHandler = (input: unknown) => Promise<unknown> | unknown;

export class DemoExecutor implements ActionExecutor {
  constructor(private readonly builtins: Record<string, BuiltinHandler>) {}

  async executeBuiltinCall(
    action: BuiltinCallAction,
    _context: ExecutionContext,
  ): Promise<BuiltinResult> {
    const handler = this.builtins[action.name];

    if (!handler) {
      throw new Error(`Unknown builtin: ${action.name}`);
    }

    return {
      ok: true,
      output: await handler(action.input),
    };
  }
}
