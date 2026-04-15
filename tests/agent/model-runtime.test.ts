import assert from "node:assert/strict";
import test from "node:test";

import type { LanguageModelV3GenerateResult } from "@ai-sdk/provider";
import { MockLanguageModelV3, mockValues } from "ai/test";

import type { ModelContextView } from "../../src/agent/types.js";
import { runDemo } from "../../src/demo/run-demo.js";
import {
  createRuntimeModel,
} from "../../src/model/runtime-model.js";
import { readRuntimeModelConfig } from "../../src/model/runtime-config.js";
import { VercelAiModelClient } from "../../src/model/vercel-ai-model-client.js";

test("runtime model config defaults to demo mode", () => {
  const config = readRuntimeModelConfig({});

  assert.deepEqual(config, {
    mode: "demo",
  });
});

test("runtime model config rejects dev mode without model id", () => {
  assert.throws(
    () =>
      readRuntimeModelConfig({
        AGENT_MODEL_MODE: "dev",
        OPENAI_API_KEY: "test-key",
      }),
    /AGENT_MODEL_MODE=dev requires AGENT_MODEL_ID to be set\./,
  );
});

test("runtime model config rejects unsupported providers", () => {
  assert.throws(
    () =>
      readRuntimeModelConfig({
        AGENT_MODEL_MODE: "dev",
        AGENT_MODEL_ID: "bedrock:claude-sonnet",
      }),
    /Unsupported AGENT_MODEL_ID provider: bedrock/,
  );
});

test("runtime model config requires the matching provider api key", () => {
  assert.throws(
    () =>
      readRuntimeModelConfig({
        AGENT_MODEL_MODE: "dev",
        AGENT_MODEL_ID: "anthropic:claude-sonnet-4-5",
      }),
    /ANTHROPIC_API_KEY must be set\./,
  );
});

test("runtime model config reads a generic base url override", () => {
  const config = readRuntimeModelConfig({
    AGENT_MODEL_MODE: "dev",
    AGENT_MODEL_ID: "openai:gpt-4.1",
    OPENAI_API_KEY: "test-openai-key",
    AGENT_MODEL_BASE_URL: "https://proxy.example.com/v1",
  });

  assert.deepEqual(config, {
    mode: "dev",
    modelId: "openai:gpt-4.1",
    provider: "openai",
    modelName: "gpt-4.1",
    apiKey: "test-openai-key",
    baseURL: "https://proxy.example.com/v1",
  });
});

test("createRuntimeModel uses DemoModel in demo mode", () => {
  const model = createRuntimeModel({
    env: {
      AGENT_MODEL_MODE: "demo",
    },
  });

  assert.equal(model.constructor.name, "DemoModel");
});

test("createRuntimeModel builds a VercelAiModelClient in dev mode", () => {
  const seenConfigs: Array<Record<string, unknown>> = [];
  const model = createRuntimeModel({
    env: {
      AGENT_MODEL_MODE: "dev",
      AGENT_MODEL_ID: "openai:gpt-4.1",
      OPENAI_API_KEY: "test-openai-key",
    },
    resolveDevLanguageModel: (config) => {
      seenConfigs.push(config);
      return new MockLanguageModelV3({
        doGenerate: createTextGenerateResult(
          JSON.stringify({
            type: "final_answer",
            answer: "done",
          }),
        ),
      });
    },
  });

  assert.equal(model.constructor.name, "VercelAiModelClient");
  assert.deepEqual(seenConfigs, [
    {
      mode: "dev",
      modelId: "openai:gpt-4.1",
      provider: "openai",
      modelName: "gpt-4.1",
      apiKey: "test-openai-key",
      baseURL: undefined,
    },
  ]);
});

test("VercelAiModelClient maps a structured final_answer", async () => {
  const client = new VercelAiModelClient({
    model: new MockLanguageModelV3({
      doGenerate: createTextGenerateResult(
        JSON.stringify({
          type: "final_answer",
          answer: "This is the final answer.",
        }),
      ),
    }),
    modelId: "openai:gpt-4.1",
  });

  const action = await client.decideNextAction(createModelContextView());

  assert.deepEqual(action, {
    type: "final_answer",
    answer: "This is the final answer.",
  });
});

test("VercelAiModelClient adds a callId to structured tool calls", async () => {
  const client = new VercelAiModelClient({
    model: new MockLanguageModelV3({
      doGenerate: createTextGenerateResult(
        JSON.stringify({
          type: "tool_call",
          toolName: "lookupOrder",
          input: {
            orderId: "ORD-1001",
          },
        }),
      ),
    }),
    modelId: "anthropic:claude-sonnet-4-5",
  });

  const action = await client.decideNextAction(
    createModelContextView({
      currentStep: 1,
    }),
  );

  assert.deepEqual(action, {
    type: "tool_call",
    callId: "call-2-lookup-order",
    toolName: "lookupOrder",
    input: {
      orderId: "ORD-1001",
    },
  });
});

test("VercelAiModelClient rejects invalid structured output", async () => {
  const client = new VercelAiModelClient({
    model: new MockLanguageModelV3(),
    modelId: "openai:gpt-4.1",
    generateStructuredAction: async () => ({
      type: "tool_call",
      toolName: "lookupOrder",
      input: {
        estimatedDelivery: 123,
      },
    }),
  });

  await assert.rejects(
    () => client.decideNextAction(createModelContextView()),
    /Invalid input/,
  );
});

test("runDemo can complete the full loop with a VercelAiModelClient in dev mode", async () => {
  const nextResult = mockValues(
    createTextGenerateResult(
      JSON.stringify({
        type: "tool_call",
        toolName: "lookupOrder",
        input: {
          orderId: "ORD-1001",
        },
      }),
    ),
    createTextGenerateResult(
      JSON.stringify({
        type: "tool_call",
        toolName: "draftReply",
        input: {
          orderId: "ORD-1001",
          status: "shipped",
          estimatedDelivery: "2026-04-18",
        },
      }),
    ),
    createTextGenerateResult(
      JSON.stringify({
        type: "final_answer",
        answer: "Your order ORD-1001 has shipped and is expected to arrive by 2026-04-18.",
      }),
    ),
  );

  const mockModel = new MockLanguageModelV3({
    doGenerate: async () => nextResult(),
  });

  const result = await runDemo("Where is order ORD-1001?", {
    model: new VercelAiModelClient({
      model: mockModel,
      modelId: "openai:gpt-4.1",
    }),
  });

  assert.equal(result.status, "completed");
  assert.equal(
    result.answer,
    "Your order ORD-1001 has shipped and is expected to arrive by 2026-04-18.",
  );
  assert.equal(result.modelCallCount, 3);
  assert.equal(result.toolCallCount, 2);
  assert.equal(mockModel.doGenerateCalls.length, 3);
});

function createModelContextView(
  overrides: Partial<ModelContextView> = {},
): ModelContextView {
  return {
    sessionId: "session-1",
    userInput: "Where is order ORD-1001?",
    currentStep: 0,
    modelCallCount: 0,
    toolCallCount: 0,
    recentEvents: [],
    messages: [
      {
        role: "user",
        content: "Where is order ORD-1001?",
      },
    ],
    permissions: ["orders:read"],
    metadata: undefined,
    ...overrides,
  };
}

function createTextGenerateResult(text: string): LanguageModelV3GenerateResult {
  return {
    content: [
      {
        type: "text",
        text,
      },
    ],
    finishReason: {
      unified: "stop",
      raw: "stop",
    },
    usage: {
      inputTokens: {
        total: 10,
        noCache: 10,
        cacheRead: 0,
        cacheWrite: 0,
      },
      outputTokens: {
        total: 10,
        text: 10,
        reasoning: 0,
      },
    },
    warnings: [],
  };
}
