import { runAgentLoop } from "../agent/agent-loop.js";
import type { AgentRunResult } from "../agent/types.js";
import { DemoExecutor } from "./demo-executor.js";
import { DemoModel } from "./demo-model.js";

export async function runDemo(userInput: string): Promise<AgentRunResult> {
  const model = new DemoModel();
  const executor = new DemoExecutor();

  return runAgentLoop({
    model,
    executor,
    userInput,
    maxSteps: 3,
    permissions: ["orders:read"],
  });
}

async function printDemo(): Promise<void> {
  const result = await runDemo("Where is order ORD-1001?");
  console.log(JSON.stringify(result, null, 2));
}

if (process.env.RUN_AGENT_DEMO === "true") {
  await printDemo();
}
