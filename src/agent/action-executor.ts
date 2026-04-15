import type { BuiltinCallAction, BuiltinResult, ExecutionContext } from "./types.js";

export interface ActionExecutor {
  executeBuiltinCall(action: BuiltinCallAction, context: ExecutionContext): Promise<BuiltinResult>;
}
