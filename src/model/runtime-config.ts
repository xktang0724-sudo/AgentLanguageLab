export type ModelRuntimeEnvironment = Readonly<Record<string, string | undefined>>;

export type AgentModelMode = "demo" | "dev";

export type SupportedModelProvider = "openai" | "anthropic";

export type DemoRuntimeModelConfig = {
  mode: "demo";
};

export type DevRuntimeModelConfig = {
  mode: "dev";
  modelId: string;
  provider: SupportedModelProvider;
  modelName: string;
  apiKey: string;
  baseURL?: string;
};

export type RuntimeModelConfig = DemoRuntimeModelConfig | DevRuntimeModelConfig;

export function readRuntimeModelConfig(
  env: ModelRuntimeEnvironment = process.env,
): RuntimeModelConfig {
  const mode = readAgentModelMode(env);
  if (mode === "demo") {
    return { mode };
  }

  const { provider, modelName, modelId } = parseModelId(readRequiredModelId(env));
  const apiKeyName = provider === "openai" ? "OPENAI_API_KEY" : "ANTHROPIC_API_KEY";
  const apiKey = readRequiredEnv(env, apiKeyName);
  const baseURL = readOptionalBaseUrl(env, provider);

  return {
    mode,
    modelId,
    provider,
    modelName,
    apiKey,
    baseURL,
  };
}

export function readAgentModelMode(
  env: ModelRuntimeEnvironment = process.env,
): AgentModelMode {
  const mode = env.AGENT_MODEL_MODE ?? "demo";
  if (mode === "demo" || mode === "dev") {
    return mode;
  }

  throw new Error(
    `Unsupported AGENT_MODEL_MODE: ${mode}. Expected "demo" or "dev".`,
  );
}

export function parseModelId(modelId: string): {
  provider: SupportedModelProvider;
  modelName: string;
  modelId: string;
} {
  const separatorIndex = modelId.indexOf(":");
  if (separatorIndex <= 0 || separatorIndex === modelId.length - 1) {
    throw new Error(
      `Invalid AGENT_MODEL_ID: ${modelId}. Expected "<provider>:<model-name>".`,
    );
  }

  const provider = modelId.slice(0, separatorIndex);
  const modelName = modelId.slice(separatorIndex + 1);
  if (provider !== "openai" && provider !== "anthropic") {
    throw new Error(
      `Unsupported AGENT_MODEL_ID provider: ${provider}. Expected "openai" or "anthropic".`,
    );
  }

  return {
    provider,
    modelName,
    modelId,
  };
}

function readRequiredModelId(env: ModelRuntimeEnvironment): string {
  return readRequiredEnv(
    env,
    "AGENT_MODEL_ID",
    "AGENT_MODEL_MODE=dev requires AGENT_MODEL_ID to be set.",
  );
}

function readRequiredEnv(
  env: ModelRuntimeEnvironment,
  key: string,
  message?: string,
): string {
  const value = env[key];
  if (typeof value === "string" && value.length > 0) {
    return value;
  }

  throw new Error(message ?? `${key} must be set.`);
}

function readOptionalBaseUrl(
  env: ModelRuntimeEnvironment,
  provider: SupportedModelProvider,
): string | undefined {
  const genericBaseUrl = env.AGENT_MODEL_BASE_URL;
  if (typeof genericBaseUrl === "string" && genericBaseUrl.length > 0) {
    return genericBaseUrl;
  }

  const providerBaseUrlKey =
    provider === "openai" ? "OPENAI_BASE_URL" : "ANTHROPIC_BASE_URL";
  const providerBaseUrl = env[providerBaseUrlKey];

  if (typeof providerBaseUrl === "string" && providerBaseUrl.length > 0) {
    return providerBaseUrl;
  }

  return undefined;
}
