export type FinalAnswerAction = {
  type: "final_answer";
  answer: string;
};

export type AskUserAction = {
  type: "ask_user";
  question: string;
};

export type HandoffToHumanAction = {
  type: "handoff_to_human";
  reason: string;
};

export type ToolCallAction<TName extends string = string> = {
  type: "tool_call";
  callId: string;
  toolName: TName;
  input: unknown;
};

export type AgentAction =
  | FinalAnswerAction
  | AskUserAction
  | HandoffToHumanAction
  | ToolCallAction;

export type ExecutionContext = Readonly<{
  sessionId: string;
  currentStep: number;
  traceId: string;
  userId?: string;
  permissions: readonly string[];
  metadata?: Readonly<Record<string, unknown>>;
}>;

export type ToolDefinition<TInput, TOutput, TName extends string = string> = {
  name: TName;
  description: string;
  validate(input: unknown): TInput;
  execute(input: TInput, context: ExecutionContext): Promise<TOutput>;
};

export type ToolObservation = {
  kind: "tool_result";
  callId: string;
  toolName: string;
  ok: boolean;
  output?: unknown;
  error?: string;
};

export type Message = {
  role: "user" | "assistant" | "tool";
  content: unknown;
};

export type AgentTraceItem =
  | {
      kind: "model_decision";
      action: AgentAction;
    }
  | {
      kind: "tool_observation";
      action: ToolCallAction;
      observation: ToolObservation;
    };

export type AgentSessionStatus =
  | "running"
  | "completed"
  | "needs_user_input"
  | "handoff_requested"
  | "failed"
  | "max_steps_exceeded";

export type AgentSessionState = {
  sessionId: string;
  traceId: string;
  userId?: string;
  userInput: string;
  currentStep: number;
  modelCallCount: number;
  toolCallCount: number;
  status: AgentSessionStatus;
  permissions: readonly string[];
  messages: Message[];
  trace: AgentTraceItem[];
  metadata?: Record<string, unknown>;
};

export type ModelContextView = {
  sessionId: string;
  userInput: string;
  currentStep: number;
  modelCallCount: number;
  toolCallCount: number;
  recentEvents: readonly AgentTraceItem[];
  messages: readonly Message[];
  permissions: readonly string[];
  metadata?: Readonly<Record<string, unknown>>;
};

export type AgentRunResult = {
  status: "completed" | "needs_user_input" | "handoff_requested" | "max_steps_exceeded";
  answer: string | null;
  question: string | null;
  handoffReason: string | null;
  steps: number;
  modelCallCount: number;
  toolCallCount: number;
  trace: AgentTraceItem[];
};
