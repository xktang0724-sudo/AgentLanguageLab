import { createProviderRegistry, type LanguageModel } from "ai";
import { createAnthropic } from "@ai-sdk/anthropic";
import { createOpenAI } from "@ai-sdk/openai";

import type { ModelClient } from "../agent/model-client.js";
import { DemoModel } from "../demo/demo-model.js";
import {
  readRuntimeModelConfig,
  type DevRuntimeModelConfig,
  type ModelRuntimeEnvironment,
} from "./runtime-config.js";
import {
  type GenerateStructuredAction,
  VercelAiModelClient,
} from "./vercel-ai-model-client.js";

type CreateRuntimeModelOptions = {
  env?: ModelRuntimeEnvironment;
  resolveDevLanguageModel?: (config: DevRuntimeModelConfig) => LanguageModel;
  generateStructuredAction?: GenerateStructuredAction;
};

export function createRuntimeModel(
  options: CreateRuntimeModelOptions = {},
): ModelClient {
  const env = options.env ?? process.env;
  const config = readRuntimeModelConfig(env);
  if (config.mode === "demo") {
    return new DemoModel();
  }

  return new VercelAiModelClient({
    model: (options.resolveDevLanguageModel ?? resolveDevLanguageModel)(config),
    modelId: config.modelId,
    generateStructuredAction: options.generateStructuredAction,
  });
}

export function resolveDevLanguageModel(config: DevRuntimeModelConfig): LanguageModel {
  if (config.provider === "openai") {
    const registry = createProviderRegistry({
      openai: createOpenAI({
        apiKey: config.apiKey,
        baseURL: config.baseURL,
      }),
    });

    return registry.languageModel(config.modelId as `openai:${string}`);
  }

  const registry = createProviderRegistry({
    anthropic: createAnthropic({
      apiKey: config.apiKey,
      baseURL: config.baseURL,
    }),
  });

  return registry.languageModel(config.modelId as `anthropic:${string}`);
}
