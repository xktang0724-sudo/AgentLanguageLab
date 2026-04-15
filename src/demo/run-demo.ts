import { runAgentLoop } from "../agent/agent-loop.js";
import type { ModelClient } from "../agent/model-client.js";
import type { AgentRunResult } from "../agent/types.js";
import { loadRuntimeEnvFiles } from "../model/load-env.js";
import { createRuntimeModel } from "../model/runtime-model.js";
import type { ModelRuntimeEnvironment } from "../model/runtime-config.js";
import { DemoExecutor } from "./demo-executor.js";

loadRuntimeEnvFiles();

type RunDemoOptions = {
  env?: ModelRuntimeEnvironment;
  model?: ModelClient;
};

export async function runDemo(
  userInput: string,
  options: RunDemoOptions = {},
): Promise<AgentRunResult> {
  const model = options.model ?? createRuntimeModel({ env: options.env });
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
