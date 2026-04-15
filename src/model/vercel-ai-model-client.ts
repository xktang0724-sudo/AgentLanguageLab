import { generateText, Output, type LanguageModel } from "ai";
import { z } from "zod";

import type { ModelClient } from "../agent/model-client.js";
import type { AgentAction, ModelContextView } from "../agent/types.js";
import { formatDemoToolCatalog, ORDER_STATUS_VALUES } from "../demo/demo-tool-catalog.js";

const lookupOrderInputSchema = z.object({
  orderId: z.string().min(1),
});

const draftReplyInputSchema = z.object({
  orderId: z.string().min(1),
  status: z.enum(ORDER_STATUS_VALUES),
  estimatedDelivery: z.string().nullable(),
});

const structuredAgentActionSchema = z.union([
  z.object({
    type: z.literal("final_answer"),
    answer: z.string().min(1),
  }),
  z.object({
    type: z.literal("ask_user"),
    question: z.string().min(1),
  }),
  z.object({
    type: z.literal("handoff_to_human"),
    reason: z.string().min(1),
  }),
  z.object({
    type: z.literal("tool_call"),
    toolName: z.literal("lookupOrder"),
    input: lookupOrderInputSchema,
  }),
  z.object({
    type: z.literal("tool_call"),
    toolName: z.literal("draftReply"),
    input: draftReplyInputSchema,
  }),
]);

type StructuredAgentAction = z.infer<typeof structuredAgentActionSchema>;

export type GenerateStructuredActionInput = {
  model: LanguageModel;
  context: ModelContextView;
  system: string;
  prompt: string;
};

export type GenerateStructuredAction = (
  input: GenerateStructuredActionInput,
) => Promise<unknown>;

type VercelAiModelClientOptions = {
  model: LanguageModel;
  modelId: string;
  generateStructuredAction?: GenerateStructuredAction;
};

export class VercelAiModelClient implements ModelClient {
  private readonly model: LanguageModel;
  private readonly modelId: string;
  private readonly generateStructuredAction: GenerateStructuredAction;

  constructor(options: VercelAiModelClientOptions) {
    this.model = options.model;
    this.modelId = options.modelId;
    this.generateStructuredAction =
      options.generateStructuredAction ?? generateStructuredActionWithAiSdk;
  }

  async decideNextAction(context: ModelContextView): Promise<AgentAction> {
    const system = buildSystemPrompt(this.modelId);
    const prompt = buildPrompt(context);
    const rawAction = await this.generateStructuredAction({
      model: this.model,
      context,
      system,
      prompt,
    });
    const action = structuredAgentActionSchema.parse(rawAction);

    return normalizeStructuredAction(action, context.currentStep);
  }
}

async function generateStructuredActionWithAiSdk(
  input: GenerateStructuredActionInput,
): Promise<StructuredAgentAction> {
  const { output } = await generateText({
    model: input.model,
    system: input.system,
    prompt: input.prompt,
    temperature: 0,
    output: Output.object({
      name: "AgentAction",
      description: "The single next action that the customer-support agent loop should take.",
      schema: structuredAgentActionSchema,
    }),
  });

  return output;
}

function normalizeStructuredAction(
  action: StructuredAgentAction,
  currentStep: number,
): AgentAction {
  if (action.type !== "tool_call") {
    return action;
  }

  return {
    type: "tool_call",
    callId: createToolCallId(currentStep, action.toolName),
    toolName: action.toolName,
    input: action.input,
  };
}

function createToolCallId(currentStep: number, toolName: string): string {
  return `call-${currentStep + 1}-${toKebabCase(toolName)}`;
}

function toKebabCase(value: string): string {
  return value.replace(/([a-z0-9])([A-Z])/g, "$1-$2").toLowerCase();
}

function buildSystemPrompt(modelId: string): string {
  return [
    "You are the decision-making model for a customer-support agent loop.",
    `The current model id is ${modelId}.`,
    "Return exactly one structured AgentAction object.",
    "Do not answer as free-form text.",
    "Do not pretend that a tool has already run when it has not.",
    "Use ask_user when the order number is missing.",
    "Use handoff_to_human when the request mentions fraud, chargeback, lawyer, or legal risk.",
    "Use lookupOrder before draftReply.",
    "Use draftReply only after a successful lookupOrder result exists.",
    "If a required tool observation failed or is missing, prefer handoff_to_human instead of guessing.",
    "After a successful draftReply result exists, final_answer should match the draft string from that tool result.",
  ].join("\n");
}

function buildPrompt(context: ModelContextView): string {
  return [
    "Choose the next single action for the agent loop.",
    "",
    "Available tools:",
    formatDemoToolCatalog(),
    "",
    "Current context JSON:",
    JSON.stringify(serializeContext(context), null, 2),
  ].join("\n");
}

function serializeContext(context: ModelContextView): Record<string, unknown> {
  return {
    sessionId: context.sessionId,
    userInput: context.userInput,
    currentStep: context.currentStep,
    modelCallCount: context.modelCallCount,
    toolCallCount: context.toolCallCount,
    permissions: [...context.permissions],
    messages: context.messages,
    recentEvents: context.recentEvents,
    metadata: context.metadata ?? null,
  };
}
