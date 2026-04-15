import type { ActionExecutor } from "./action-executor.js";
import type { ModelClient } from "./model-client.js";
import type { AgentRunResult, AgentSessionState, AgentTraceItem, ExecutionContext, Message, ModelContextView } from "./types.js";

export type RunAgentLoopInput = {
  model: ModelClient;
  executor: ActionExecutor;
  userInput: string;
  maxSteps: number;
  sessionId?: string;
  metadata?: Record<string, unknown>;
};

export async function runAgentLoop(input: RunAgentLoopInput): Promise<AgentRunResult> {
  const state: AgentSessionState = {
    sessionId: input.sessionId ?? createSessionId(),
    userInput: input.userInput,
    currentStep: 0,
    status: "running",
    messages: [
      {
        role: "user",
        content: input.userInput,
      },
    ],
    trace: [],
    metadata: input.metadata ? { ...input.metadata } : undefined,
  };

  try {
    while (state.currentStep < input.maxSteps) {
      const context = createModelContextView(state);

      const action = await input.model.decideNextAction(context);
      state.trace.push({
        kind: "model_decision",
        action,
      });

      if (action.type === "final_answer") {
        state.status = "completed";
        state.messages.push({
          role: "assistant",
          content: action.answer,
        });

        return createRunResult(state, action.answer);
      }

      const result = await input.executor.executeBuiltinCall(action, createExecutionContext(state));
      state.trace.push({
        kind: "action_result",
        action,
        result,
      });
      state.messages.push(createToolMessage(action.name, result.output));
      state.currentStep += 1;
    }
  } catch (error) {
    state.status = "failed";
    throw error;
  }

  state.status = "max_steps_exceeded";

  return createRunResult(state, null);
}

function createRunResult(state: AgentSessionState, answer: string | null): AgentRunResult {
  return {
    status: state.status === "completed" ? "completed" : "max_steps_exceeded",
    answer,
    steps: state.currentStep,
    trace: state.trace,
  };
}

function createModelContextView(state: AgentSessionState): ModelContextView {
  return {
    sessionId: state.sessionId,
    userInput: state.userInput,
    currentStep: state.currentStep,
    recentEvents: cloneReadonly(state.trace),
    messages: cloneReadonly(state.messages),
    metadata: state.metadata ? cloneReadonly(state.metadata) : undefined,
  };
}

function createExecutionContext(state: AgentSessionState): ExecutionContext {
  return {
    sessionId: state.sessionId,
    currentStep: state.currentStep,
    metadata: state.metadata ? cloneReadonly(state.metadata) : undefined,
  };
}

function createToolMessage(name: string, output: unknown): Message {
  return {
    role: "tool",
    content: {
      name,
      output,
    },
  };
}

function cloneReadonly<T>(value: T): Readonly<T> {
  return deepFreeze(structuredClone(value));
}

function deepFreeze<T>(value: T): Readonly<T> {
  if (value !== null && typeof value === "object" && !Object.isFrozen(value)) {
    for (const nestedValue of Object.values(value as Record<string, unknown>)) {
      deepFreeze(nestedValue);
    }
    Object.freeze(value);
  }

  return value as Readonly<T>;
}

function createSessionId(): string {
  return `session-${Date.now()}`;
}
