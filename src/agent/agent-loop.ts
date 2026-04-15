import type { ActionExecutor } from "./action-executor.js";
import type { ModelClient } from "./model-client.js";
import type {
  AgentAction,
  AgentRunResult,
  AgentSessionState,
  ExecutionContext,
  Message,
  ModelContextView,
  ToolCallAction,
  ToolObservation,
} from "./types.js";

export type RunAgentLoopInput = {
  model: ModelClient;
  executor: ActionExecutor;
  userInput: string;
  maxSteps: number;
  sessionId?: string;
  traceId?: string;
  userId?: string;
  permissions?: readonly string[];
  metadata?: Record<string, unknown>;
};

export async function runAgentLoop(input: RunAgentLoopInput): Promise<AgentRunResult> {
  const state: AgentSessionState = {
    sessionId: input.sessionId ?? createSessionId(),
    traceId: input.traceId ?? createTraceId(),
    userId: input.userId,
    userInput: input.userInput,
    currentStep: 0,
    modelCallCount: 0,
    toolCallCount: 0,
    status: "running",
    permissions: input.permissions ? [...input.permissions] : [],
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
      state.modelCallCount += 1;
      state.trace.push({
        kind: "model_decision",
        action,
      });

      const terminalResult = handleTerminalAction(state, action);
      if (terminalResult) {
        return terminalResult;
      }
      if (action.type !== "tool_call") {
        throw new Error(`Unsupported action type: ${action.type}`);
      }

      const observation = await input.executor.executeToolCall(
        action,
        createExecutionContext(state),
      );
      state.toolCallCount += 1;
      state.trace.push({
        kind: "tool_observation",
        action,
        observation,
      });
      state.messages.push(createToolMessage(action, observation));
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
    status: normalizeRunStatus(state.status),
    answer,
    question: null,
    handoffReason: null,
    steps: state.modelCallCount,
    modelCallCount: state.modelCallCount,
    toolCallCount: state.toolCallCount,
    trace: state.trace,
  };
}

function createModelContextView(state: AgentSessionState): ModelContextView {
  return {
    sessionId: state.sessionId,
    userInput: state.userInput,
    currentStep: state.currentStep,
    modelCallCount: state.modelCallCount,
    toolCallCount: state.toolCallCount,
    recentEvents: cloneReadonly(state.trace),
    messages: cloneReadonly(state.messages),
    permissions: cloneReadonly([...state.permissions]),
    metadata: state.metadata ? cloneReadonly(state.metadata) : undefined,
  };
}

function createExecutionContext(state: AgentSessionState): ExecutionContext {
  return {
    sessionId: state.sessionId,
    currentStep: state.currentStep,
    traceId: state.traceId,
    userId: state.userId,
    permissions: cloneReadonly([...state.permissions]),
    metadata: state.metadata ? cloneReadonly(state.metadata) : undefined,
  };
}

function createToolMessage(action: ToolCallAction, observation: ToolObservation): Message {
  return {
    role: "tool",
    content: {
      callId: action.callId,
      toolName: action.toolName,
      ok: observation.ok,
      output: observation.output,
      error: observation.error,
    },
  };
}

function handleTerminalAction(
  state: AgentSessionState,
  action: AgentAction,
): AgentRunResult | null {
  if (action.type === "final_answer") {
    state.status = "completed";
    state.messages.push({
      role: "assistant",
      content: action.answer,
    });

    return createRunResult(state, action.answer);
  }

  if (action.type === "ask_user") {
    state.status = "needs_user_input";
    state.messages.push({
      role: "assistant",
      content: action.question,
    });

    return {
      ...createRunResult(state, null),
      status: "needs_user_input",
      question: action.question,
    };
  }

  if (action.type === "handoff_to_human") {
    state.status = "handoff_requested";
    state.messages.push({
      role: "assistant",
      content: action.reason,
    });

    return {
      ...createRunResult(state, null),
      status: "handoff_requested",
      handoffReason: action.reason,
    };
  }

  return null;
}

function normalizeRunStatus(status: AgentSessionState["status"]): AgentRunResult["status"] {
  if (
    status === "completed" ||
    status === "needs_user_input" ||
    status === "handoff_requested"
  ) {
    return status;
  }

  return "max_steps_exceeded";
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

function createTraceId(): string {
  return `trace-${Date.now()}`;
}
