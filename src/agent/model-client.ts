import type { AgentAction, ModelContextView } from "./types.js";

export interface ModelClient {
  decideNextAction(context: ModelContextView): Promise<AgentAction>;
}
